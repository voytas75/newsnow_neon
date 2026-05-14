"""Smoke tests for startup/bootstrap seams without invoking the GUI mainloop."""

from __future__ import annotations

import importlib.util
import types

import pytest

from newsnow_neon.main import (
    TKINTER_IMPORT_ERROR_MESSAGE,
    bootstrap_app,
    load_app_class,
    main,
)


def test_load_app_class_wraps_missing_tkinter_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing tkinter should be surfaced as an explicit runtime dependency error."""
    main_module = importlib.import_module("newsnow_neon.main")

    def fake_import_module(name: str) -> types.ModuleType:
        raise ModuleNotFoundError("No module named 'tkinter'", name="tkinter")

    monkeypatch.setattr(main_module.importlib, "import_module", fake_import_module)

    with pytest.raises(RuntimeError, match="Tkinter is not available"):
        load_app_class()


def test_bootstrap_app_returns_app_without_running_mainloop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bootstrap should instantiate the app but not start the GUI loop."""
    main_module = importlib.import_module("newsnow_neon.main")
    events: list[str] = []

    class FakeApp:
        def __init__(self) -> None:
            events.append("init")

        def mainloop(self) -> None:
            events.append("mainloop")

    monkeypatch.setattr(main_module, "load_app_class", lambda: FakeApp)

    app = bootstrap_app()

    assert isinstance(app, FakeApp)
    assert events == ["init"]


def test_bootstrap_app_loads_settings_override_when_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bootstrap should apply an explicit settings override before launch."""
    main_module = importlib.import_module("newsnow_neon.main")
    calls: list[str] = []

    class FakeApp:
        def load_settings_override(self, path: str) -> None:
            calls.append(path)

    monkeypatch.setattr(main_module, "load_app_class", lambda: FakeApp)

    app = bootstrap_app(settings_path="/tmp/settings.json")

    assert isinstance(app, FakeApp)
    assert calls == ["/tmp/settings.json"]


def test_main_bootstraps_then_runs_mainloop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Main should keep the existing public launch flow via bootstrap + mainloop."""
    main_module = importlib.import_module("newsnow_neon.main")
    events: list[str] = []

    class FakeApp:
        def mainloop(self) -> None:
            events.append("mainloop")

    def fake_bootstrap(*, settings_path: str | None = None) -> FakeApp:
        events.append(f"bootstrap:{settings_path}")
        return FakeApp()

    monkeypatch.setattr(main_module, "bootstrap_app", fake_bootstrap)

    main(settings_path="/tmp/custom.json")

    assert events == ["bootstrap:/tmp/custom.json", "mainloop"]


def test_tkinter_error_message_mentions_runtime_fix() -> None:
    """The dependency error should explain that Tk support must be installed."""
    assert "desktop Python build" in TKINTER_IMPORT_ERROR_MESSAGE
    assert "python3-tk" in TKINTER_IMPORT_ERROR_MESSAGE
