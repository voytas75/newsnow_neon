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


def test_real_tk_manual_refresh_replaces_offline_content(tmp_path: Path) -> None:
    """Invoke the real refresh button and observe its completed offline update."""
    settings_path = tmp_path / "manual-refresh-settings.json"
    script = r'''
import os
import sys
import time
from pathlib import Path

settings_path = Path(sys.argv[1])
os.environ["NEWS_APP_SETTINGS"] = str(settings_path)
os.environ["REDIS_URL"] = ""

from newsnow_neon.app import services
from newsnow_neon.models import Headline

initial = Headline(
    title="Before manual refresh",
    url="https://example.test/before-manual-refresh",
    section="Technology",
)
refreshed = Headline(
    title="After manual refresh",
    url="https://example.test/after-manual-refresh",
    section="Technology",
)
fetch_calls = []


def fetch_headlines(*, force_refresh=False):
    fetch_calls.append(force_refresh)
    if len(fetch_calls) == 1:
        return [initial], False, None
    if len(fetch_calls) == 2:
        return [refreshed], False, None
    raise AssertionError(f"unexpected fetch call: {fetch_calls!r}")


services.configure_app_services(
    fetch_headlines=fetch_headlines,
    build_ticker_text=lambda headlines: " | ".join(item.title for item in headlines),
    resolve_article_summary=lambda _headline: None,
    persist_headlines_with_ticker=lambda *_args, **_kwargs: None,
    collect_redis_statistics=lambda: None,
    clear_cached_headlines=lambda: (True, "offline refresh: cache unavailable"),
    load_historical_snapshots=lambda *_args, **_kwargs: [],
)

from newsnow_neon.application import AINewsApp

app = AINewsApp()
succeeded = False
deadline = time.monotonic() + 3


def find_button(label):
    pending = list(app.winfo_children())
    while pending:
        widget = pending.pop()
        if widget.winfo_class() == "Button" and widget.cget("text") == label:
            return widget
        pending.extend(widget.winfo_children())
    raise AssertionError(f"button not found: {label}")


def ticker_titles(ticker):
    return [
        ticker._headline_groups[group_tag]["full_title"]
        for group_tag in ticker.headline_order
    ]


def finish_error(error):
    print(f"manual_refresh_error={error!r}", file=sys.stderr)
    app.destroy()
    raise SystemExit(1)


def wait_for_refresh():
    global succeeded
    try:
        app.update_idletasks()
        list_text = app.listbox.get("1.0", "end-1c")
        if refreshed.title not in list_text:
            if time.monotonic() < deadline:
                app.after(25, wait_for_refresh)
                return
            raise AssertionError(f"refresh result not rendered: {list_text!r}")

        assert fetch_calls == [False, True]
        assert initial.title not in list_text
        for ticker in (app.ticker, app.full_ticker):
            titles = ticker_titles(ticker)
            assert any(refreshed.title in title for title in titles), titles
            assert all(initial.title not in title for title in titles), titles
    except BaseException as error:
        finish_error(error)
    else:
        succeeded = True
        print("manual_refresh=ok")
        app.destroy()


def wait_for_initial_render():
    try:
        app.update_idletasks()
        list_text = app.listbox.get("1.0", "end-1c")
        if initial.title not in list_text:
            if time.monotonic() < deadline:
                app.after(25, wait_for_initial_render)
                return
            raise AssertionError(f"initial content not rendered: {list_text!r}")

        assert fetch_calls == [False]
        find_button("Refresh Now").invoke()
        app.after(0, wait_for_refresh)
    except BaseException as error:
        finish_error(error)


app.after(0, wait_for_initial_render)
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
    assert "manual_refresh=ok" in result.stdout


def test_real_tk_search_and_section_filter_update_list_and_tickers(
    tmp_path: Path,
) -> None:
    """Exercise the real triage controls against deterministic offline headlines."""
    settings_path = tmp_path / "search-filter-settings.json"
    script = r'''
import os
import sys
import time
from pathlib import Path

settings_path = Path(sys.argv[1])
os.environ["NEWS_APP_SETTINGS"] = str(settings_path)
os.environ["REDIS_URL"] = ""

from newsnow_neon.app import services
from newsnow_neon.models import Headline

technology_ai = Headline(
    title="AI platform launch",
    url="https://example.test/ai-platform",
    section="Technology",
)
business_market = Headline(
    title="Market update",
    url="https://example.test/market-update",
    section="Business",
)
technology_security = Headline(
    title="Security update",
    url="https://example.test/security-update",
    section="Technology",
)
headlines = [technology_ai, business_market, technology_security]
fetch_calls = []


def fetch_headlines(*, force_refresh=False):
    fetch_calls.append(force_refresh)
    return headlines, False, None


services.configure_app_services(
    fetch_headlines=fetch_headlines,
    build_ticker_text=lambda entries: " | ".join(item.title for item in entries),
    resolve_article_summary=lambda _headline: None,
    persist_headlines_with_ticker=lambda *_args, **_kwargs: None,
    collect_redis_statistics=lambda: None,
    clear_cached_headlines=lambda: (True, "offline filters: cache unavailable"),
    load_historical_snapshots=lambda *_args, **_kwargs: [],
)

from newsnow_neon.application import AINewsApp

app = AINewsApp()
succeeded = False
deadline = time.monotonic() + 3
all_titles = [item.title for item in headlines]
technology_titles = [technology_ai.title, technology_security.title]
security_titles = [technology_security.title]


def ticker_titles(ticker):
    return [
        ticker._headline_groups[group_tag]["full_title"]
        for group_tag in ticker.headline_order
    ]


def view_matches(expected_titles):
    list_text = app.listbox.get("1.0", "end-1c")
    unexpected_titles = [title for title in all_titles if title not in expected_titles]
    if not all(title in list_text for title in expected_titles):
        return False
    if any(title in list_text for title in unexpected_titles):
        return False
    for ticker in (app.ticker, app.full_ticker):
        titles = ticker_titles(ticker)
        if not all(
            any(expected in title for title in titles)
            for expected in expected_titles
        ):
            return False
        if any(
            any(unexpected in title for title in titles)
            for unexpected in unexpected_titles
        ):
            return False
    return True


def finish_error(error):
    print(f"search_filter_error={error!r}", file=sys.stderr)
    app.destroy()
    raise SystemExit(1)


def wait_for_view(expected_titles, next_step):
    try:
        app.update_idletasks()
        if not view_matches(expected_titles):
            if time.monotonic() < deadline:
                app.after(25, lambda: wait_for_view(expected_titles, next_step))
                return
            list_text = app.listbox.get("1.0", "end-1c")
            raise AssertionError(f"expected {expected_titles!r}, got {list_text!r}")
        next_step()
    except BaseException as error:
        finish_error(error)


def select_section(label):
    menu = app.section_filter_menu["menu"]
    end = menu.index("end")
    if end is None:
        raise AssertionError("section filter has no menu entries")
    for index in range(int(end) + 1):
        if menu.entrycget(index, "label") == label:
            menu.invoke(index)
            return
    raise AssertionError(f"section menu entry not found: {label}")


def clear_search():
    for widget in app.search_entry.master.winfo_children():
        if widget.winfo_class() == "Button" and widget.cget("text") == "Clear":
            widget.invoke()
            return
    raise AssertionError("search Clear button not found")


def finish():
    global succeeded
    assert fetch_calls == [False]
    succeeded = True
    print("search_filter=ok")
    app.destroy()


def select_all_sections():
    select_section("All sections")
    app.after(0, lambda: wait_for_view(all_titles, finish))


def clear_query():
    clear_search()
    app.after(0, lambda: wait_for_view(technology_titles, select_all_sections))


def enter_query():
    app.search_entry.insert(0, "security")
    app.after(0, lambda: wait_for_view(security_titles, clear_query))


def select_technology():
    select_section("Technology")
    app.after(0, lambda: wait_for_view(technology_titles, enter_query))


app.after(0, lambda: wait_for_view(all_titles, select_technology))
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
    assert "search_filter=ok" in result.stdout


def test_real_tk_exclusion_apply_and_clear_persist_and_restore_views(
    tmp_path: Path,
) -> None:
    """Exercise persisted exclusion controls against deterministic offline headlines."""
    settings_path = tmp_path / "exclusion-settings.json"
    script = r'''
import json
import os
import sys
import time
from pathlib import Path

settings_path = Path(sys.argv[1])
os.environ["NEWS_APP_SETTINGS"] = str(settings_path)
os.environ["REDIS_URL"] = ""

from newsnow_neon.app import services
from newsnow_neon.models import Headline

ai_headline = Headline(
    title="AI platform launch",
    url="https://example.test/ai-platform",
    section="Technology",
)
market_headline = Headline(
    title="Market update",
    url="https://example.test/market-update",
    section="Business",
)
security_headline = Headline(
    title="Security bulletin",
    url="https://example.test/security-bulletin",
    section="Technology",
)
headlines = [ai_headline, market_headline, security_headline]
fetch_calls = []


def fetch_headlines(*, force_refresh=False):
    fetch_calls.append(force_refresh)
    return headlines, False, None


services.configure_app_services(
    fetch_headlines=fetch_headlines,
    build_ticker_text=lambda entries: " | ".join(item.title for item in entries),
    resolve_article_summary=lambda _headline: None,
    persist_headlines_with_ticker=lambda *_args, **_kwargs: None,
    collect_redis_statistics=lambda: None,
    clear_cached_headlines=lambda: (True, "offline exclusions: cache unavailable"),
    load_historical_snapshots=lambda *_args, **_kwargs: [],
)

from newsnow_neon.application import AINewsApp

app = AINewsApp()
succeeded = False
deadline = time.monotonic() + 3
all_titles = [item.title for item in headlines]
remaining_titles = [market_headline.title, security_headline.title]


def ticker_titles(ticker):
    return [
        ticker._headline_groups[group_tag]["full_title"]
        for group_tag in ticker.headline_order
    ]


def view_matches(expected_titles):
    list_text = app.listbox.get("1.0", "end-1c")
    unexpected_titles = [title for title in all_titles if title not in expected_titles]
    if not all(title in list_text for title in expected_titles):
        return False
    if any(title in list_text for title in unexpected_titles):
        return False
    for ticker in (app.ticker, app.full_ticker):
        titles = ticker_titles(ticker)
        if not all(
            any(expected in title for title in titles)
            for expected in expected_titles
        ):
            return False
        if any(
            any(unexpected in title for title in titles)
            for unexpected in unexpected_titles
        ):
            return False
    return True


def stored_exclusions():
    with settings_path.open(encoding="utf-8") as handle:
        return json.load(handle)["headline_exclusions"]


def exclusion_button(label):
    after_entry = False
    for widget in app.exclude_entry.master.winfo_children():
        if widget is app.exclude_entry:
            after_entry = True
            continue
        if (
            after_entry
            and widget.winfo_class() == "Button"
            and widget.cget("text") == label
        ):
            return widget
    raise AssertionError(f"exclude button not found: {label}")


def finish_error(error):
    print(f"exclusion_flow_error={error!r}", file=sys.stderr)
    app.destroy()
    raise SystemExit(1)


def wait_for_view(expected_titles, next_step):
    try:
        app.update_idletasks()
        if not view_matches(expected_titles):
            if time.monotonic() < deadline:
                app.after(25, lambda: wait_for_view(expected_titles, next_step))
                return
            list_text = app.listbox.get("1.0", "end-1c")
            raise AssertionError(f"expected {expected_titles!r}, got {list_text!r}")
        next_step()
    except BaseException as error:
        finish_error(error)


def finish():
    global succeeded
    assert app.exclude_terms_var.get() == ""
    assert stored_exclusions() == []
    assert fetch_calls == [False]
    succeeded = True
    print("exclusion_flow=ok")
    app.destroy()


def clear_exclusions():
    assert app.exclude_terms_var.get() == "ai"
    assert stored_exclusions() == ["ai"]
    exclusion_button("Clear").invoke()
    app.after(0, lambda: wait_for_view(all_titles, finish))


def apply_exclusions():
    app.exclude_entry.insert(0, "AI, ai")
    exclusion_button("Apply").invoke()
    app.after(0, lambda: wait_for_view(remaining_titles, clear_exclusions))


app.after(0, lambda: wait_for_view(all_titles, apply_exclusions))
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
    assert "exclusion_flow=ok" in result.stdout


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
