"""Auto-refresh scheduling controller.

Updates: v0.52 - 2025-11-18 - Minimal wrappers around application methods.
"""
from __future__ import annotations


class AutoRefreshController:
    """Delegates scheduling to the application for now."""

    def __init__(self, app) -> None:
        self.app = app

    def schedule(self) -> None:
        self.app._schedule_auto_refresh()

    def schedule_with_delay(self, delay_ms: int) -> None:
        self.app._schedule_auto_refresh_with_delay(delay_ms)
