"""UI package aggregator for NewsNow Neon.

Updates: v0.52 - 2025-11-18 - Re-exported split widgets and windows for stable imports.
"""

from __future__ import annotations

from .widgets.news_ticker import NewsTicker
from .windows.summary_window import SummaryWindow
from .windows.keyword_heatmap_window import KeywordHeatmapWindow
from .windows.redis_stats_window import RedisStatsWindow
from .windows.app_info_window import AppInfoWindow

__all__ = [
    "NewsTicker",
    "SummaryWindow",
    "KeywordHeatmapWindow",
    "RedisStatsWindow",
    "AppInfoWindow",
]