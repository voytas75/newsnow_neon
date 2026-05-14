"""Controller package re-exports.

Updates: v0.52 - 2025-11-18 - Introduced controller package and stubs
to allow application.py delegation without import errors.
Updates: v0.53.1 - 2026-05-14 - Made package exports lazy so importing
`newsnow_neon.app.controller` does not eagerly import Tk-bound submodules.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "RefreshController",
    "AutoRefreshController",
    "BackgroundWatchController",
    "HistoryController",
    "SelectionController",
    "ExclusionsController",
    "SettingsController",
    "RedisController",
    "HighlightController",
    "AINewsApp",
]

_MODULE_EXPORTS = {
    "RefreshController": ".refresh_controller",
    "AutoRefreshController": ".auto_refresh_controller",
    "BackgroundWatchController": ".background_watch_controller",
    "HistoryController": ".history_controller",
    "SelectionController": ".selection_controller",
    "ExclusionsController": ".exclusions_controller",
    "SettingsController": ".settings_controller",
    "RedisController": ".redis_controller",
    "HighlightController": ".highlight_controller",
    "AINewsApp": "newsnow_neon.application",
}


def __getattr__(name: str) -> Any:
    """Resolve controller exports lazily to avoid eager Tk-bound imports."""
    module_name = _MODULE_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    if name == "AINewsApp":
        from newsnow_neon.application import AINewsApp

        return AINewsApp

    from importlib import import_module

    module = import_module(module_name, __name__)
    return getattr(module, name)
