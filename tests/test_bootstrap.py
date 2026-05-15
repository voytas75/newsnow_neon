"""Smoke tests for startup/bootstrap seams and package-surface compatibility."""

from __future__ import annotations

import importlib
import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

from newsnow_neon.main import (
    HEADLESS_DISPLAY_ERROR_MESSAGE,
    TKINTER_IMPORT_ERROR_MESSAGE,
    bootstrap_app,
    collect_startup_diagnostics,
    configure_legacy_runtime_services,
    is_headless_tk_error,
    load_app_class,
    main,
    render_startup_diagnostics,
    render_startup_error,
    run_startup_diagnostics,
)


def _run_entrypoint_without_tkinter(
    tmp_path: Path,
    command: list[str],
) -> subprocess.CompletedProcess[str]:
    """Run a front door in a subprocess with ``tkinter`` import blocked."""
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        """
import builtins

_real_import = builtins.__import__


def _blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == \"tkinter\" or name.startswith(\"tkinter.\"):
        raise ModuleNotFoundError(\"No module named 'tkinter'\", name=\"tkinter\")
    return _real_import(name, globals, locals, fromlist, level)


builtins.__import__ = _blocked_import
""".strip()
        + "\n",
        encoding="utf-8",
    )
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{tmp_path}{os.pathsep}{repo_root}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else f"{tmp_path}{os.pathsep}{repo_root}"
    )

    return subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )


def test_app_controller_package_import_is_lazy() -> None:
    """Importing the controller package should not eagerly load Tk-bound submodules."""
    controller_pkg = importlib.import_module("newsnow_neon.app.controller")

    assert controller_pkg.__name__ == "newsnow_neon.app.controller"
    assert "HistoryController" in controller_pkg.__all__
    assert "newsnow_neon.app.controller.history_controller" not in sys.modules


def test_app_controller_package_exposes_lazy_ainnewsapp_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The package export for AINewsApp should resolve lazily via __getattr__."""
    controller_pkg = importlib.import_module("newsnow_neon.app.controller")
    fake_application = types.ModuleType("newsnow_neon.application")

    class FakeAINewsApp:
        pass

    fake_application.AINewsApp = FakeAINewsApp
    monkeypatch.setitem(sys.modules, "newsnow_neon.application", fake_application)

    assert controller_pkg.AINewsApp is FakeAINewsApp


def test_app_services_package_exports_news_service_module() -> None:
    """The services package should expose its modular news service surface."""
    news_service = importlib.import_module("newsnow_neon.app.services.news_service")

    assert news_service.__name__ == "newsnow_neon.app.services.news_service"
    assert hasattr(news_service, "fetch_headlines")


def test_app_controller_file_wrapper_matches_package_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The file wrapper should expose the same AINewsApp symbol as the package."""
    controller_pkg = importlib.import_module("newsnow_neon.app.controller")
    controller_file = importlib.util.spec_from_file_location(
        "newsnow_neon.app._controller_file",
        Path(__file__).resolve().parents[1] / "newsnow_neon" / "app" / "controller.py",
    )
    assert controller_file is not None and controller_file.loader is not None

    fake_application = types.ModuleType("newsnow_neon.application")

    class FakeAINewsApp:
        pass

    fake_application.AINewsApp = FakeAINewsApp
    monkeypatch.setitem(sys.modules, "newsnow_neon.application", fake_application)

    controller_file_module = importlib.util.module_from_spec(controller_file)
    controller_file.loader.exec_module(controller_file_module)

    assert controller_pkg.AINewsApp is FakeAINewsApp
    assert controller_file_module.AINewsApp is FakeAINewsApp


def test_load_app_class_wraps_missing_non_tk_runtime_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing non-Tk runtime deps should surface as a bounded startup error."""
    main_module = importlib.import_module("newsnow_neon.main")

    def fake_import_module(name: str) -> types.ModuleType:
        raise ModuleNotFoundError("No module named 'bs4'", name="bs4")

    monkeypatch.setattr(main_module.importlib, "import_module", fake_import_module)

    with pytest.raises(
        RuntimeError,
        match="required runtime dependency `bs4` is missing",
    ):
        load_app_class()


def test_load_app_class_configures_runtime_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loading the app class should also wire legacy runtime services explicitly."""
    main_module = importlib.import_module("newsnow_neon.main")
    configured: list[object] = []

    class FakeApp:
        pass

    class FakeLegacyModule:
        AINewsApp = FakeApp
        fetch_headlines = staticmethod(lambda *args, **kwargs: ([], False, None))
        build_ticker_text = staticmethod(lambda headlines: "ticker")
        resolve_article_summary = staticmethod(lambda headline: {"summary": True})
        persist_headlines_with_ticker = staticmethod(lambda *args, **kwargs: None)
        collect_redis_statistics = staticmethod(lambda: object())
        clear_cached_headlines = staticmethod(lambda: (True, "ok"))
        load_historical_snapshots = staticmethod(lambda *args, **kwargs: [])

    monkeypatch.setattr(
        main_module.importlib,
        "import_module",
        lambda name: FakeLegacyModule,
    )
    monkeypatch.setattr(
        main_module,
        "configure_legacy_runtime_services",
        lambda legacy_module: configured.append(legacy_module),
    )

    assert load_app_class() is FakeApp
    assert configured == [FakeLegacyModule]


def test_configure_legacy_runtime_services_binds_service_proxies() -> None:
    """Legacy startup wiring should configure app services explicitly."""
    from newsnow_neon.app import services as service_module

    calls: list[str] = []

    class LegacyModule:
        @staticmethod
        def fetch_headlines(
            *args: object,
            **kwargs: object,
        ) -> tuple[list[object], bool, str | None]:
            calls.append("fetch")
            return [], False, None

        @staticmethod
        def build_ticker_text(headlines: object) -> str:
            calls.append("ticker")
            return "ticker"

        @staticmethod
        def resolve_article_summary(headline: object) -> object:
            calls.append("summary")
            return {"summary": True}

        @staticmethod
        def persist_headlines_with_ticker(*args: object, **kwargs: object) -> None:
            calls.append("persist")

        @staticmethod
        def collect_redis_statistics() -> object:
            calls.append("redis")
            return object()

        @staticmethod
        def clear_cached_headlines() -> tuple[bool, str]:
            calls.append("clear")
            return True, "ok"

        @staticmethod
        def load_historical_snapshots(*args: object, **kwargs: object) -> list[object]:
            calls.append("history")
            return []

    configure_legacy_runtime_services(LegacyModule)

    assert service_module.fetch_headlines() == ([], False, None)
    assert service_module.build_ticker_text([]) == "ticker"
    assert service_module.resolve_article_summary(object()) == {"summary": True}
    service_module.persist_headlines_with_ticker()
    assert service_module.collect_redis_statistics() is not None
    assert service_module.clear_cached_headlines() == (True, "ok")
    assert service_module.load_historical_snapshots() == []
    assert calls == [
        "fetch",
        "ticker",
        "summary",
        "persist",
        "redis",
        "clear",
        "history",
    ]


def test_configure_legacy_runtime_services_rebinds_application_runtime_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Application runtime should read services through the live registry after rebinding."""
    fake_application = types.ModuleType("newsnow_neon.application")

    class FakeAINewsApp:
        def _refresh_worker(self, force_refresh: bool) -> None:
            import newsnow_neon.app.services as app_services
            from datetime import datetime

            try:
                fetched_at = datetime.now()
                headlines, from_cache, cached_ticker = app_services.fetch_headlines(
                    force_refresh=force_refresh
                )
                if from_cache:
                    ticker_text = cached_ticker or app_services.build_ticker_text(headlines)
                    should_update_cache = bool(headlines) and not cached_ticker
                else:
                    ticker_text = app_services.build_ticker_text(headlines)
                    should_update_cache = bool(headlines)
                if should_update_cache:
                    app_services.persist_headlines_with_ticker(headlines, ticker_text)
            except Exception as exc:  # pragma: no cover - should stay green here
                self.after(0, lambda error=exc: self._handle_fetch_error(error))
                return

            self.after(
                0,
                lambda: self._handle_refresh_result(
                    headlines=headlines,
                    ticker_text=ticker_text,
                    from_cache=from_cache,
                    fetched_at=fetched_at,
                ),
            )

    fake_application.AINewsApp = FakeAINewsApp
    fake_application.configure_app_services = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "newsnow_neon.application", fake_application)

    application_module = importlib.import_module("newsnow_neon.application")

    calls: list[str] = []

    class LegacyModule:
        @staticmethod
        def fetch_headlines(
            *args: object,
            **kwargs: object,
        ) -> tuple[list[object], bool, str | None]:
            calls.append("fetch")
            return ["headline"], False, None

        @staticmethod
        def build_ticker_text(headlines: object) -> str:
            calls.append("ticker")
            return "ticker-from-legacy"

        @staticmethod
        def resolve_article_summary(headline: object) -> object:
            return {"summary": True}

        @staticmethod
        def persist_headlines_with_ticker(*args: object, **kwargs: object) -> None:
            calls.append("persist")

        @staticmethod
        def collect_redis_statistics() -> object:
            return object()

        @staticmethod
        def clear_cached_headlines() -> tuple[bool, str]:
            return True, "ok"

        @staticmethod
        def load_historical_snapshots(*args: object, **kwargs: object) -> list[object]:
            return []

    configure_legacy_runtime_services(LegacyModule)

    scheduled: list[tuple[int, object]] = []
    handled: list[dict[str, object]] = []

    class RefreshWorkerApp:
        def after(self, delay: int, callback) -> None:
            scheduled.append((delay, callback))
            callback()

        def _handle_refresh_result(
            self,
            *,
            headlines,
            ticker_text: str,
            from_cache: bool,
            fetched_at,
        ) -> None:
            handled.append(
                {
                    "headlines": headlines,
                    "ticker_text": ticker_text,
                    "from_cache": from_cache,
                    "fetched_at": fetched_at,
                }
            )

        def _handle_fetch_error(self, error: Exception) -> None:
            raise AssertionError(f"unexpected fetch error: {error}")

    app = RefreshWorkerApp()

    application_module.AINewsApp._refresh_worker(app, force_refresh=False)

    assert len(scheduled) == 1
    assert handled[0]["headlines"] == ["headline"]
    assert handled[0]["ticker_text"] == "ticker-from-legacy"
    assert handled[0]["from_cache"] is False
    assert calls == ["fetch", "ticker", "persist"]


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


def test_render_startup_error_maps_headless_tk_error() -> None:
    """Headless Tk failures should map to a clearer CLI-facing message."""

    class FakeTclError(Exception):
        pass

    error = FakeTclError("no display name and no $DISPLAY environment variable")

    assert is_headless_tk_error(error)
    assert render_startup_error(error) == HEADLESS_DISPLAY_ERROR_MESSAGE


def test_collect_startup_diagnostics_reports_runtime_readiness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics should report Python/Tk/display/settings readiness.

    The check must stay GUI-free.
    """
    main_module = importlib.import_module("newsnow_neon.main")

    monkeypatch.setattr(main_module, "detect_tkinter_runtime", lambda: None)
    monkeypatch.setattr(main_module, "has_display_environment", lambda: True)
    monkeypatch.setattr(
        main_module,
        "resolve_settings_path",
        lambda: tmp_path / "settings.json",
    )
    monkeypatch.setattr(main_module, "is_settings_path_writable", lambda path: True)

    report = collect_startup_diagnostics()
    rendered = render_startup_diagnostics(report)

    assert report["required_ready"] is True
    assert report["required_failures"] == []
    assert "Verdict: READY" in rendered
    assert "- Tkinter available" in rendered
    assert "- Display available" in rendered
    assert "- Settings path writable" in rendered


def test_run_startup_diagnostics_returns_exit_1_when_required_prereq_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics should fail the readiness contract when a required check fails."""
    main_module = importlib.import_module("newsnow_neon.main")

    monkeypatch.setattr(
        main_module,
        "detect_tkinter_runtime",
        lambda: (_ for _ in ()).throw(RuntimeError(TKINTER_IMPORT_ERROR_MESSAGE)),
    )
    monkeypatch.setattr(main_module, "has_display_environment", lambda: False)
    monkeypatch.setattr(
        main_module,
        "resolve_settings_path",
        lambda: tmp_path / "settings.json",
    )
    monkeypatch.setattr(main_module, "is_settings_path_writable", lambda path: False)

    with pytest.raises(SystemExit, match="1"):
        run_startup_diagnostics()


def test_main_prints_headless_message_and_exits(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Headless GUI startup should print a user-facing error instead of a traceback."""
    main_module = importlib.import_module("newsnow_neon.main")

    def fake_bootstrap(*, settings_path: str | None = None) -> object:
        class FakeTclError(Exception):
            pass

        class FakeApp:
            def mainloop(self) -> None:
                raise FakeTclError(
                    "no display name and no $DISPLAY environment variable"
                )

        return FakeApp()

    monkeypatch.setattr(main_module, "bootstrap_app", fake_bootstrap)

    with pytest.raises(SystemExit, match="1"):
        main()

    captured = capsys.readouterr()
    assert HEADLESS_DISPLAY_ERROR_MESSAGE in captured.err


def test_python_module_entrypoint_check_reports_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--check` should print diagnostics and avoid launching the GUI."""
    package_main = importlib.import_module("newsnow_neon.__main__")
    diagnostics_output = (
        "Verdict: NOT READY\n"
        "problem / missing prerequisite\n"
        "- Tkinter missing"
    )
    called: list[str] = []

    monkeypatch.setattr(package_main, "main", lambda: called.append("gui"))

    def fake_run_startup_diagnostics() -> str:
        print(diagnostics_output)
        raise SystemExit(1)

    monkeypatch.setattr(
        package_main,
        "run_startup_diagnostics",
        fake_run_startup_diagnostics,
    )
    monkeypatch.setattr(package_main.sys, "argv", ["newsnow_neon", "--check"])

    with pytest.raises(SystemExit, match="1"):
        package_main._run()

    captured = capsys.readouterr()
    assert diagnostics_output in captured.out
    assert called == []


