"""Persistent settings helpers for the NewsNow Neon application.

This module centralises the load/save logic for user preferences so both the
legacy entrypoint and newly modularised components can reuse the same
implementation.

Updates: v0.50 - 2025-01-07 - Moved settings persistence helpers from the legacy script.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .config import DEFAULT_SETTINGS, SETTINGS_PATH, set_historical_cache_enabled

logger = logging.getLogger(__name__)


def _normalise_auto_refresh_minutes(value: Any) -> int:
    """Return a persisted refresh interval safe for the Tk integer variable."""
    default = int(DEFAULT_SETTINGS["auto_refresh_minutes"])
    if isinstance(value, bool):
        return default
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(180, minutes))


def load_settings() -> dict[str, Any]:
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
    settings["auto_refresh_minutes"] = _normalise_auto_refresh_minutes(
        settings.get("auto_refresh_minutes")
    )
    set_historical_cache_enabled(
        bool(
            settings.get(
                "historical_cache_enabled",
                DEFAULT_SETTINGS["historical_cache_enabled"],
            )
        )
    )
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    """Persist application settings to disk."""
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SETTINGS_PATH.open("w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
    except Exception as exc:  # pragma: no cover - IO issues
        logger.warning("Unable to save settings: %s", exc)


__all__ = ["load_settings", "save_settings"]
