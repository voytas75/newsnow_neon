"""History controller.

Updates: v0.52 - 2025-11-18 - Minimal wrappers for history workflows.
"""
from __future__ import annotations
from typing import Optional
from ..models import HistoricalSnapshot  # type: ignore


class HistoryController:
    """Delegates history interactions to the application."""

    def __init__(self, app) -> None:
        self.app = app

    def request_refresh(self) -> None:
        self.app._request_history_refresh()

    def apply_snapshot(self, snapshot: "HistoricalSnapshot") -> None:
        self.app._apply_history_snapshot(snapshot)
