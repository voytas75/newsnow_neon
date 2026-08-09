"""Offline real-Tk smoke coverage for the primary NewsNowNeon workflow."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from newsnow_neon.main import has_display_environment

pytestmark = pytest.mark.skipif(
    not has_display_environment(),
    reason="A graphical display is required for the real-Tk smoke test.",
)


def test_real_tk_renders_offline_headline_without_live_services(tmp_path: Path) -> None:
    """Build the real GUI and render one offline headline in an isolated process."""
    settings_path = tmp_path / "gui-smoke-settings.json"
    script = r'''
import os
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
os.environ["NEWS_APP_SETTINGS"] = str(settings_path)
os.environ["REDIS_URL"] = ""

from newsnow_neon.app import services
from newsnow_neon.models import Headline

headline = Headline(
    title="Offline GUI smoke headline",
    url="https://example.test/newsnow-neon-gui-smoke",
    section="Technology",
)
services.configure_app_services(
    fetch_headlines=lambda **_kwargs: ([headline], False, None),
    build_ticker_text=lambda headlines: " | ".join(item.title for item in headlines),
    resolve_article_summary=lambda _headline: None,
    persist_headlines_with_ticker=lambda *_args, **_kwargs: None,
    collect_redis_statistics=lambda: None,
    clear_cached_headlines=lambda: (True, "offline smoke: cache unavailable"),
    load_historical_snapshots=lambda *_args, **_kwargs: [],
)

from newsnow_neon.application import AINewsApp

app = AINewsApp()
succeeded = False


def verify() -> None:
    global succeeded
    try:
        app.update_idletasks()
        assert app.title() == "NewsNow Neon"
        assert app.listbox.winfo_ismapped()
        assert app.ticker.winfo_ismapped()
        assert "Offline GUI smoke headline" in app.listbox.get("1.0", "end-1c")

        app._toggle_options_panel()
        app.update_idletasks()
        visible_bottom = app.winfo_rooty() + app.winfo_height()
        pending = list(app.winfo_children())
        headings = {}
        while pending:
            widget = pending.pop()
            if widget.winfo_class() == "Label":
                label = widget.cget("text")
                if label in {"Appearance & Readability", "Monitoring & Runtime"}:
                    headings[label] = widget
            pending.extend(widget.winfo_children())

        assert set(headings) == {"Appearance & Readability", "Monitoring & Runtime"}
        for label, widget in headings.items():
            assert widget.winfo_ismapped(), f"{label} is not mapped"
            assert widget.winfo_rooty() + widget.winfo_height() <= visible_bottom, (
                f"{label} is outside the visible default geometry"
            )

        color_controls = {}
        pending = list(app.winfo_children())
        while pending:
            widget = pending.pop()
            if widget.winfo_class() == "Button":
                label = widget.cget("text")
                if label in {"Background…", "Text…"}:
                    color_controls[label] = widget
            pending.extend(widget.winfo_children())

        assert set(color_controls) == {"Background…", "Text…"}
        for label, widget in color_controls.items():
            assert widget.winfo_ismapped(), f"{label} is not mapped"
            assert widget.winfo_height() == widget.winfo_reqheight(), (
                f"{label} is vertically clipped"
            )
            assert widget.winfo_rooty() + widget.winfo_height() <= visible_bottom, (
                f"{label} is outside the visible default geometry"
            )

        app._toggle_options_panel()
        app.update_idletasks()
        assert app.options_toggle_btn.cget("text") == "Show Controls"
        assert app.listbox.winfo_ismapped()
        assert "Offline GUI smoke headline" in app.listbox.get("1.0", "end-1c")
    except BaseException as error:
        print(f"gui_smoke_error={error!r}", file=sys.stderr)
    else:
        succeeded = True
        print("gui_smoke=ok")
    finally:
        app.destroy()


app.after(750, verify)
app.mainloop()
raise SystemExit(0 if succeeded else 1)
'''
    environment = os.environ.copy()
    environment["NEWS_APP_SETTINGS"] = str(settings_path)
    environment["REDIS_URL"] = ""

    result = subprocess.run(
        [sys.executable, "-c", script, str(settings_path)],
        capture_output=True,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "gui_smoke=ok" in result.stdout


def test_real_tk_restores_custom_appearance_across_restart(tmp_path: Path) -> None:
    """Persist custom appearance in one real-Tk process and restore it in another."""
    settings_path = tmp_path / "appearance-round-trip-settings.json"
    script = r'''
import os
import sys
from pathlib import Path

mode = sys.argv[1]
settings_path = Path(sys.argv[2])
os.environ["NEWS_APP_SETTINGS"] = str(settings_path)
os.environ["REDIS_URL"] = ""

from newsnow_neon.app import services
from newsnow_neon.app.ui.ui_helpers import update_ticker_colors
from newsnow_neon.config import CUSTOM_PROFILE_NAME
from newsnow_neon.models import Headline

EXPECTED_BACKGROUND = "#123456"
EXPECTED_TEXT = "#fedcba"
EXPECTED_SPEED = 7
headline = Headline(
    title="Offline appearance round-trip",
    url="https://example.test/newsnow-neon-appearance-round-trip",
    section="Technology",
)
services.configure_app_services(
    fetch_headlines=lambda **_kwargs: ([headline], False, None),
    build_ticker_text=lambda headlines: " | ".join(item.title for item in headlines),
    resolve_article_summary=lambda _headline: None,
    persist_headlines_with_ticker=lambda *_args, **_kwargs: None,
    collect_redis_statistics=lambda: None,
    clear_cached_headlines=lambda: (True, "offline appearance: cache unavailable"),
    load_historical_snapshots=lambda *_args, **_kwargs: [],
)

from newsnow_neon.application import AINewsApp

app = AINewsApp()
succeeded = False


def verify() -> None:
    global succeeded
    try:
        app.update_idletasks()
        if mode == "write":
            app.ticker_speed_var.set(EXPECTED_SPEED)
            app._apply_speed()
            app.ticker_bg_var.set(EXPECTED_BACKGROUND)
            app.ticker_fg_var.set(EXPECTED_TEXT)
            update_ticker_colors(app)
        elif mode == "verify":
            assert app.color_profile_var.get() == CUSTOM_PROFILE_NAME
            assert app.ticker_speed_var.get() == EXPECTED_SPEED
            assert app.ticker.speed == EXPECTED_SPEED
            for ticker in (app.ticker, app.full_ticker):
                assert ticker.bg_color == EXPECTED_BACKGROUND
                assert ticker.text_color == EXPECTED_TEXT
        else:
            raise AssertionError(f"unsupported mode: {mode}")
    except BaseException as error:
        print(f"appearance_round_trip_error={error!r}", file=sys.stderr)
    else:
        succeeded = True
        print(f"appearance_round_trip_{mode}=ok")
    finally:
        app.destroy()


app.after(750, verify)
app.mainloop()
raise SystemExit(0 if succeeded else 1)
'''
    environment = os.environ.copy()
    environment["NEWS_APP_SETTINGS"] = str(settings_path)
    environment["REDIS_URL"] = ""

    for mode in ("write", "verify"):
        result = subprocess.run(
            [sys.executable, "-c", script, mode, str(settings_path)],
            capture_output=True,
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert f"appearance_round_trip_{mode}=ok" in result.stdout
