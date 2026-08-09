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
