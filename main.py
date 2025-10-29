"""Application entrypoint wiring for NewsNow Neon.

The full Tkinter orchestration still lives in the packaged legacy
``legacy_app.py`` module. The goal is to migrate that logic into dedicated
layers over time.

Updates: v0.49.1 - 2025-01-07 - Added metadata factory and stub main routine.
Updates: v0.49.2 - 2025-10-29 - Switched to packaged legacy module and removed reliance on root-level script.
Updates: v0.49.4 - 2025-10-30 - Hardcoded author and support metadata to avoid env dependencies.
"""

from __future__ import annotations

import importlib
import logging
from typing import Optional

from .models import AppMetadata

logger = logging.getLogger(__name__)

APP_VERSION = "0.49"
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


def main(settings_path: Optional[str] = None) -> None:
    """Launch the NewsNow Neon Tk application."""

    logger.debug("Bootstrapping NewsNow Neon main loop")

    legacy_app = importlib.import_module("newsnow_neon_app.legacy_app")

    app = legacy_app.AINewsApp()
    if settings_path:
        try:
            app.load_settings_override(settings_path)  # type: ignore[attr-defined]
        except AttributeError:
            logger.warning("AINewsApp has no settings override hook yet.")
    app.mainloop()


__all__ = ["APP_METADATA", "APP_VERSION", "main"]
