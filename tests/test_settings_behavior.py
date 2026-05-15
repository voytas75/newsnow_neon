"""Settings and operator-control behavior tests.

Updates: v0.53.1 - 2026-05-15 - Added bounded tests for settings persistence and control clamping.
Updates: v0.53.2 - 2026-05-15 - Added bounded persistence tests for exclusion and highlight controls.
"""
from __future__ import annotations

from types import SimpleNamespace
import sys
import types

import pytest


if "tkinter" in sys.modules:
    tk_module = sys.modules["tkinter"]
    if not hasattr(tk_module, "colorchooser"):
        tk_module.colorchooser = types.SimpleNamespace(askcolor=lambda **_kwargs: (None, None))
    if not hasattr(tk_module, "messagebox"):
        tk_module.messagebox = types.SimpleNamespace(
            showinfo=lambda *args, **kwargs: None,
            showwarning=lambda *args, **kwargs: None,
        )
    if not hasattr(tk_module, "NORMAL"):
        tk_module.NORMAL = "normal"
    if not hasattr(tk_module, "DISABLED"):
        tk_module.DISABLED = "disabled"

from newsnow_neon.app.controller.background_watch_controller import (
    BackgroundWatchController,
)
from newsnow_neon.app.controller.exclusions_controller import ExclusionsController
from newsnow_neon.app.controller.highlight_controller import HighlightController
from newsnow_neon.app.ui.ui_helpers import set_options_visibility
from newsnow_neon.config import DEFAULT_SETTINGS
from newsnow_neon.settings_store import load_settings, save_settings


class DummyContainer:
    def __init__(self) -> None:
        self._mapped = False
        self.pack_calls: list[dict[str, object]] = []
        self.pack_forget_calls = 0

    def winfo_ismapped(self) -> bool:
        return self._mapped

    def pack(self, **kwargs: object) -> None:
        self._mapped = True
        self.pack_calls.append(kwargs)

    def pack_forget(self) -> None:
        self._mapped = False
        self.pack_forget_calls += 1


class DummyButton:
    def __init__(self) -> None:
        self.text_history: list[str] = []
        self.state_history: list[str] = []

    def config(self, *, text: str | None = None, state: str | None = None) -> None:
        if text is not None:
            self.text_history.append(text)
        if state is not None:
            self.state_history.append(state)


class DummyLabel:
    def __init__(self) -> None:
        self.pack_calls: list[dict[str, object]] = []
        self._mapped = False

    def winfo_ismapped(self) -> bool:
        return self._mapped

    def pack(self, **kwargs: object) -> None:
        self._mapped = True
        self.pack_calls.append(kwargs)

    def pack_forget(self) -> None:
        self._mapped = False


class DummyVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value) -> None:
        self.value = value


class DummySpinboxVar:
    def __init__(self, value) -> None:
        self.value = value

    def get(self):
        return self.value

    def set(self, value) -> None:
        self.value = value


class SettingsLikeApp:
    def __init__(self) -> None:
        self._options_visible = False
        self.options_container = DummyContainer()
        self.options_toggle_btn = DummyButton()
        self.status_summary_label = DummyLabel()
        self.status_summary_var = DummyVar("")
        self.background_watch_var = DummyVar(False)
        self.auto_refresh_var = DummyVar(False)
        self.new_headlines_var = DummyVar("New headlines pending: 0")
        self.last_refresh_var = DummyVar("Last refresh: pending")
        self.next_refresh_var = DummyVar("Next refresh: paused")
        self.settings = {"options_visible": False}
        self.saved_settings: list[dict[str, object]] = []

    def _save_settings(self) -> None:
        self.saved_settings.append(dict(self.settings))


class BackgroundWatchApp:
    def __init__(self, *, threshold: int = 30, current: int = 30, saved: int | None = None) -> None:
        self.settings = {"background_watch_refresh_threshold": threshold}
        self.background_watch_threshold_var = DummySpinboxVar(current)
        self._background_refresh_threshold = saved if saved is not None else threshold
        self.saved_calls = 0
        self.auto_refresh_checks = 0

    def _save_settings(self) -> None:
        self.saved_calls += 1

    def _filtered_entries(self):  # pragma: no cover - not used in these tests
        return []

    def _headline_key(self, headline):  # pragma: no cover - not used in these tests
        raise NotImplementedError

    background_watch_var = DummyVar(True)
    _history_mode = False
    _pending_new_headlines = 0
    _background_watch_running = False
    _refresh_job = None
    _background_candidate_keys = set()


class ExclusionsApp:
    def __init__(self, initial_var: str = "", initial_terms: set[str] | None = None, initial_settings: list[str] | None = None) -> None:
        self.exclude_terms_var = DummyVar(initial_var)
        self._exclusion_terms = initial_terms or set()
        self.settings = {"headline_exclusions": initial_settings or []}
        self.saved_calls = 0
        self.reapply_calls: list[bool] = []

    def _save_settings(self) -> None:
        self.saved_calls += 1

    def _reapply_exclusion_filters(self, *, log_status: bool) -> None:
        self.reapply_calls.append(log_status)


class HeatmapWindowStub:
    def __init__(self, *, exists: bool = True) -> None:
        self._exists = exists
        self.destroy_calls = 0
        self.updated_with = None

    def winfo_exists(self) -> bool:
        return self._exists

    def destroy(self) -> None:
        self.destroy_calls += 1
        self._exists = False

    def update_data(self, headlines) -> None:
        self.updated_with = headlines


class HighlightApp:
    def __init__(self, initial_value: str = "") -> None:
        self.highlight_keywords_var = DummyVar(initial_value)
        self.settings = {"highlight_keywords": initial_value}
        self.saved_calls = 0
        self.status_messages: list[str] = []
        self.render_calls: list[tuple[bool, bool, bool]] = []
        self.status_summary_updates = 0
        self.headlines = []
        self._raw_headlines = []
        self._heatmap_window = None
        self.heatmap_btn = DummyButton()

    def _save_settings(self) -> None:
        self.saved_calls += 1

    def _log_status(self, message: str) -> None:
        self.status_messages.append(message)

    def _render_filtered_headlines(self, *, reschedule: bool, log_status: bool, update_tickers: bool) -> None:
        self.render_calls.append((reschedule, log_status, update_tickers))

    def _update_status_summary(self) -> None:
        self.status_summary_updates += 1


@pytest.fixture()
def isolated_settings_path(tmp_path, monkeypatch):
    settings_path = tmp_path / "ainews_settings.json"
    monkeypatch.setattr("newsnow_neon.settings_store.SETTINGS_PATH", settings_path)
    return settings_path


@pytest.fixture()
def highlight_patches(monkeypatch):
    applied_payloads: list[dict[str, str]] = []

    monkeypatch.setattr(
        "newsnow_neon.app.controller.highlight_controller.apply_highlight_keywords",
        lambda payload: applied_payloads.append(dict(payload)),
    )
    monkeypatch.setattr(
        "newsnow_neon.app.controller.highlight_controller.has_highlight_pattern",
        lambda: bool(applied_payloads and applied_payloads[-1]),
    )
    return applied_payloads


def test_save_and_load_settings_round_trip_only_known_keys(isolated_settings_path) -> None:
    payload = DEFAULT_SETTINGS | {
        "auto_refresh_minutes": 17,
        "background_watch_refresh_threshold": 42,
        "options_visible": True,
        "highlight_keywords": "ai:#ff0",
        "unknown_field": "ignored",
    }

    save_settings(payload)

    loaded = load_settings()

    assert isolated_settings_path.exists()
    assert loaded["auto_refresh_minutes"] == 17
    assert loaded["background_watch_refresh_threshold"] == 42
    assert loaded["options_visible"] is True
    assert loaded["highlight_keywords"] == "ai:#ff0"
    assert "unknown_field" not in loaded


def test_set_options_visibility_persists_and_updates_toggle_copy() -> None:
    app = SettingsLikeApp()

    set_options_visibility(app, True)

    assert app._options_visible is True
    assert app.settings["options_visible"] is True
    assert app.saved_settings[-1]["options_visible"] is True
    assert app.options_toggle_btn.text_history[-1] == "Hide Controls"
    assert app.options_container.winfo_ismapped() is True


def test_set_options_visibility_can_skip_persistence() -> None:
    app = SettingsLikeApp()

    set_options_visibility(app, True, persist=False)

    assert app._options_visible is True
    assert app.settings["options_visible"] is False
    assert app.saved_settings == []


def test_set_options_visibility_uses_controls_hidden_fallback_summary() -> None:
    app = SettingsLikeApp()
    app.last_refresh_var.set("")

    set_options_visibility(app, False)

    assert app.status_summary_var.get() == "Controls hidden"
    assert app.options_toggle_btn.text_history[-1] == "Show Controls"


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [(0, 1), (1, 1), (180, 180), (999, 180), ("7", 7), ("bad", DEFAULT_SETTINGS["auto_refresh_minutes"])],
)
def test_auto_refresh_minutes_are_clamped(raw_value, expected) -> None:
    app = SimpleNamespace(auto_refresh_minutes_var=DummySpinboxVar(raw_value))

    minutes = app.auto_refresh_minutes_var.get()
    try:
        parsed = int(minutes)
    except (TypeError, ValueError):
        parsed = DEFAULT_SETTINGS["auto_refresh_minutes"]
    parsed = max(1, min(180, parsed))
    app.auto_refresh_minutes_var.set(parsed)

    assert app.auto_refresh_minutes_var.get() == expected


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [(0, 1), (1, 1), (999, 999), (1000, 999), ("41", 41), ("bad", 30)],
)
def test_background_watch_threshold_is_clamped(raw_value, expected) -> None:
    app = BackgroundWatchApp(threshold=30, current=raw_value)
    controller = BackgroundWatchController(app)
    controller.maybe_auto_refresh_for_pending = lambda: setattr(app, "auto_refresh_checks", app.auto_refresh_checks + 1)

    controller.apply_threshold()

    assert app.background_watch_threshold_var.get() == expected
    assert app.settings["background_watch_refresh_threshold"] == expected
    assert app._background_refresh_threshold == expected
    expected_save_calls = 0 if raw_value == "bad" else 1
    expected_refresh_checks = 0 if raw_value == "bad" else 1
    assert app.saved_calls == expected_save_calls
    assert app.auto_refresh_checks == expected_refresh_checks


def test_apply_exclusion_terms_persists_normalized_terms() -> None:
    app = ExclusionsApp(initial_var="AI, ai, ml")
    controller = ExclusionsController(app)

    result = controller.apply_exclusion_terms()

    assert result is None
    assert app.exclude_terms_var.get() == "ai, ml"
    assert app.settings["headline_exclusions"] == ["ai", "ml"]
    assert app._exclusion_terms == {"ai", "ml"}
    assert app.saved_calls == 1
    assert app.reapply_calls == [True]


def test_apply_exclusion_terms_skips_persist_when_terms_are_unchanged() -> None:
    app = ExclusionsApp(initial_var="AI, ml", initial_terms={"ai", "ml"}, initial_settings=["ai", "ml"])
    controller = ExclusionsController(app)

    result = controller.apply_exclusion_terms()

    assert result is None
    assert app.exclude_terms_var.get() == "ai, ml"
    assert app.saved_calls == 0
    assert app.reapply_calls == []


def test_update_keywords_setting_persists_canonical_string_and_refreshes_views(highlight_patches) -> None:
    app = HighlightApp(initial_value="")
    controller = HighlightController(app)

    controller.update_keywords_setting(
        "ai:#ff0; ml:#00f",
        refresh_views=True,
        persist=True,
        show_feedback=True,
    )

    assert app.highlight_keywords_var.get() == "ai:#ff0; ml:#00f"
    assert app.settings["highlight_keywords"] == "ai:#ff0; ml:#00f"
    assert highlight_patches[-1] == {"ai": "#ff0", "ml": "#00f"}
    assert app.saved_calls == 1
    assert app.render_calls == [(False, False, False)]
    assert app.status_messages[-1] == "Highlight keywords updated from settings."
    assert app.status_summary_updates == 1
    assert app.heatmap_btn.state_history[-1] == "normal"


def test_update_keywords_setting_keeps_nonempty_mapping_when_keyword_has_no_color(highlight_patches) -> None:
    app = HighlightApp(initial_value="existing:#fff")
    controller = HighlightController(app)

    controller.update_keywords_setting(
        "not-a-valid-pattern",
        refresh_views=False,
        persist=True,
        show_feedback=False,
    )

    assert app.highlight_keywords_var.get() == "not-a-valid-pattern:#FFD54F"
    assert app.settings["highlight_keywords"] == "not-a-valid-pattern:#FFD54F"
    assert highlight_patches[-1] == {"not-a-valid-pattern": "#FFD54F"}
    assert app.saved_calls == 1
    assert app.render_calls == []
    assert app.heatmap_btn.state_history[-1] == "normal"
