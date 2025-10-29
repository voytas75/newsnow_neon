"""Persistent settings helpers for the NewsNow Neon application.

This module centralises the load/save logic for user preferences so both the
legacy entrypoint and newly modularised components can reuse the same
implementation.

Updates: v0.50 - 2025-01-07 - Moved settings persistence helpers from the legacy script.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from .config import DEFAULT_SETTINGS, SETTINGS_PATH, set_historical_cache_enabled

logger = logging.getLogger(__name__)


def load_settings() -> Dict[str, Any]:
    """Load application settings from disk, falling back to defaults."""

    settings = DEFAULT_SETTINGS.copy()
    try:
        if SETTINGS_PATH.exists():
            with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                for key in settings:
                    if key in data:
                        settings[key] = data[key]
    except Exception as exc:  # pragma: no cover - IO issues
        logger.warning("Unable to load settings: %s", exc)
    set_historical_cache_enabled(
        bool(
            settings.get(
                "historical_cache_enabled",
                DEFAULT_SETTINGS["historical_cache_enabled"],
            )
        )
    )
    return settings


def save_settings(settings: Dict[str, Any]) -> None:
    """Persist application settings to disk."""

    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SETTINGS_PATH.open("w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
    except Exception as exc:  # pragma: no cover - IO issues
        logger.warning("Unable to save settings: %s", exc)


__all__ = ["load_settings", "save_settings"]
