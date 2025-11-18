"""Smoke tests for application metadata and entrypoint wiring.

Validates:
- APP_METADATA presence and basic field values
- APP_VERSION formatting
- Availability of callable main() entrypoint (without invoking GUI)
- Presence of __main__._run() wrapper
- Skips gracefully if tkinter is unavailable
"""

from __future__ import annotations

import pytest

# Ensure Tkinter is present before importing modules that rely on it
pytest.importorskip(
    "tkinter", reason="Tkinter not available; skipping GUI-bound metadata tests."
)

from newsnow_neon.main import APP_METADATA, APP_VERSION, main
from newsnow_neon.models import AppMetadata
from newsnow_neon.__main__ import _run


def test_app_metadata_instance_type() -> None:
    """APP_METADATA should be an AppMetadata dataclass."""
    assert isinstance(APP_METADATA, AppMetadata)


def test_app_metadata_basic_fields() -> None:
    """Validate core APP_METADATA field values."""
    assert APP_METADATA.name == "NewsNow Neon"
    assert APP_METADATA.version.startswith("v")
    assert APP_METADATA.author == "https://github.com/voytas75"
    assert APP_METADATA.donate_url == "https://ko-fi.com/voytas"
    assert "Tkinter desktop dashboard" in APP_METADATA.description


def test_app_version_constant() -> None:
    """APP_VERSION should be a simple semantic string without the 'v' prefix."""
    assert APP_VERSION == "0.49"


def test_main_callable_without_invocation() -> None:
    """Ensure main is importable and callable (do not invoke to avoid Tk mainloop)."""
    assert callable(main)


def test_run_wrapper_callable_without_invocation() -> None:
    """Ensure __main__._run exists and is callable (do not invoke)."""
    assert callable(_run)