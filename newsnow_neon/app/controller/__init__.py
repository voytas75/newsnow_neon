"""Controller package re-exports.

Updates: v0.52 - 2025-11-18 - Introduced controller package and stubs
to allow application.py delegation without import errors.
"""
from __future__ import annotations

from .refresh_controller import RefreshController
from .auto_refresh_controller import AutoRefreshController
from .background_watch_controller import BackgroundWatchController
from .history_controller import HistoryController
from .selection_controller import SelectionController
from .exclusions_controller import ExclusionsController
from .settings_controller import SettingsController
from .redis_controller import RedisController
from .highlight_controller import HighlightController

# Back-compat wrapper (if any code imports AINewsApp from app.controller)
try:
    from ..application import AINewsApp  # type: ignore
except Exception:  # pragma: no cover
    AINewsApp = None  # type: ignore

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
