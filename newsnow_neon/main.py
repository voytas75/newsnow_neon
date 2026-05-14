"""Application entrypoint wiring for NewsNow Neon.

The full Tkinter orchestration still lives in the packaged legacy
``legacy_app.py`` module. The goal is to migrate that logic into dedicated
layers over time.

Updates: v0.49.1 - 2025-01-07 - Added metadata factory and stub main routine.
Updates: v0.49.2 - 2025-10-29 - Switched to packaged legacy module and
removed reliance on root-level script.
Updates: v0.49.4 - 2025-10-30 - Hardcoded author and support metadata to
avoid env dependencies.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, cast

from .models import AppMetadata

logger = logging.getLogger(__name__)

APP_VERSION = "0.53"
TKINTER_IMPORT_ERROR_MESSAGE = (
    "Tkinter is not available in this Python runtime. Install a desktop Python build "
    "with Tk support (for example `python3-tk` on some Linux distributions)."
)
APP_METADATA = AppMetadata(
    name="NewsNow Neon",
    version=f"v{APP_VERSION}",
    author="https://github.com/voytas75",
    donate_url="https://ko-fi.com/voytas",
    description=(
        "Tkinter desktop dashboard for curated NewsNow headlines with cached summaries "
        "and live configuration controls."
    ),
)


def load_app_class() -> type[Any]:
    """Load the Tk app class while classifying missing Tk support explicitly."""
    try:
        legacy_app = importlib.import_module("newsnow_neon.legacy_app")
    except ModuleNotFoundError as exc:
        if exc.name == "tkinter":
            raise RuntimeError(TKINTER_IMPORT_ERROR_MESSAGE) from exc
        raise

    return cast(type[Any], legacy_app.AINewsApp)


def bootstrap_app(settings_path: str | None = None) -> Any:
    """Create the NewsNow Neon application instance without starting mainloop."""
    app_class = load_app_class()
    app = app_class()
    if settings_path:
        load_settings_override = getattr(app, "load_settings_override", None)
        if callable(load_settings_override):
            load_settings_override(settings_path)
        else:
            logger.warning("AINewsApp has no settings override hook yet.")
    return app


def main(settings_path: str | None = None) -> None:
    """Launch the NewsNow Neon Tk application."""
    logger.debug("Bootstrapping NewsNow Neon main loop")

    app = bootstrap_app(settings_path=settings_path)
    app.mainloop()


__all__ = [
    "APP_METADATA",
    "APP_VERSION",
    "TKINTER_IMPORT_ERROR_MESSAGE",
    "bootstrap_app",
    "load_app_class",
    "main",
]
