"""Smoke tests for startup/bootstrap seams without invoking the GUI mainloop."""

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
        f"{tmp_path}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(tmp_path)
    )

    return subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
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


def test_python_module_entrypoint_without_tkinter_shows_cli_message(
    tmp_path: Path,
) -> None:
    """`python -m newsnow_neon` without tkinter should avoid a raw traceback."""
    result = _run_entrypoint_without_tkinter(
        tmp_path,
        [sys.executable, "-m", "newsnow_neon"],
    )

    assert result.returncode == 1
    assert "Tkinter is not available" in result.stderr
    assert "Traceback" not in result.stderr


def test_console_script_entrypoint_without_tkinter_shows_cli_message(
    tmp_path: Path,
) -> None:
    """Installed console script should keep the same no-Tk CLI behavior."""
    result = _run_entrypoint_without_tkinter(
        tmp_path,
        [sys.executable, "-c", "from newsnow_neon.__main__ import _run; _run()"],
    )

    assert result.returncode == 1
    assert "Tkinter is not available" in result.stderr
    assert "Traceback" not in result.stderr


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


