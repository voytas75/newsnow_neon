"""Tkinter UI aggregator for the NewsNow Neon application.

This module was slimmed down to re-export split widgets and windows from
`newsnow_neon/ui/widgets` and `newsnow_neon/ui/windows` to preserve imports.

Updates: v0.55 - 2025-11-18 - Slimmed and delegated to ui.widgets/ui.windows.
"""

from __future__ import annotations

# Re-exported components (backward-compatible surface)
from .ui.widgets.news_ticker import NewsTicker
from .ui.windows.summary_window import SummaryWindow
from .ui.windows.keyword_heatmap_window import KeywordHeatmapWindow
from .ui.windows.redis_stats_window import RedisStatsWindow
from .ui.windows.app_info_window import AppInfoWindow

__all__ = [
    "NewsTicker",
    "SummaryWindow",
    "KeywordHeatmapWindow",
    "RedisStatsWindow",
    "AppInfoWindow",
]
