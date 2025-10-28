"""Application entrypoint wiring for NewsNow Neon.

The full Tkinter orchestration still lives in the legacy ``newsnow_neon.py``
script. The goal is to migrate that logic into dedicated layers over time.

Updates: v0.49.1 - 2025-01-07 - Added metadata factory and stub main routine.
"""

from __future__ import annotations

import importlib
import logging
from typing import Optional

from .models import AppMetadata
from .utils import read_optional_env

logger = logging.getLogger(__name__)

APP_VERSION = "0.49"
APP_METADATA = AppMetadata(
    name="NewsNow Neon",
    version=f"v{APP_VERSION}",
    author=read_optional_env("NEWSNOW_APP_AUTHOR") or "NewsNow Neon maintainers",
    donate_url=read_optional_env("NEWSNOW_DONATE_URL"),
    description=(
        "Tkinter desktop dashboard for curated NewsNow headlines with cached summaries "
        "and live configuration controls."
    ),
)


def main(settings_path: Optional[str] = None) -> None:
    """Launch the NewsNow Neon Tk application."""

    logger.debug("Bootstrapping NewsNow Neon main loop")

    legacy_app = importlib.import_module("newsnow_neon")

    app = legacy_app.AINewsApp()
    if settings_path:
        try:
            app.load_settings_override(settings_path)  # type: ignore[attr-defined]
        except AttributeError:
            logger.warning("AINewsApp has no settings override hook yet.")
    app.mainloop()


__all__ = ["APP_METADATA", "APP_VERSION", "main"]
