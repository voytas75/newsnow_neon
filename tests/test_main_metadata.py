"""Smoke tests for application metadata and entrypoint wiring.

Validates:
- APP_METADATA presence and basic field values
- APP_VERSION formatting
- Availability of callable main() entrypoint (without invoking GUI)
- Presence of __main__._run() wrapper
- Thin delegation contract between __main__ and main module
- Skips gracefully when tkinter-dependent metadata imports are unavailable
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

HAS_TKINTER = sys.modules.get("tkinter") is not None or (
    importlib.util.find_spec("tkinter") is not None
)

pytestmark = pytest.mark.skipif(
    not HAS_TKINTER,
    reason="Tkinter not available; skipping GUI-bound metadata tests.",
)


def test_app_metadata_basic_fields() -> None:
    """Validate core APP_METADATA field values."""
    from newsnow_neon.main import APP_METADATA

    assert APP_METADATA.name == "NewsNow Neon"
    assert APP_METADATA.version.startswith("v")
    assert APP_METADATA.author == "https://github.com/voytas75"
    assert APP_METADATA.donate_url == "https://ko-fi.com/voytas"
    assert "Tkinter desktop dashboard" in APP_METADATA.description


def test_app_version_constant() -> None:
    """APP_VERSION should be a simple semantic string without the 'v' prefix."""
    from newsnow_neon.main import APP_VERSION

    assert APP_VERSION == "0.53"


def test_main_callable_without_invocation() -> None:
    """Ensure main is importable and callable (do not invoke to avoid Tk mainloop)."""
    from newsnow_neon.main import main

    assert callable(main)


def test_run_wrapper_callable_without_invocation() -> None:
    """Ensure __main__._run exists and is callable (do not invoke)."""
    from newsnow_neon.__main__ import _run

    assert callable(_run)


def test_run_wrapper_delegates_to_module_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """The package front door should delegate exactly once to newsnow_neon.main.main."""
    from newsnow_neon import __main__ as package_main

    calls: list[str] = []

    def fake_main() -> None:
        calls.append("called")

    monkeypatch.setattr(package_main, "main", fake_main)

    package_main._run()

    assert calls == ["called"]
