"""Background watch controller.

Updates: v0.52 - 2025-11-18 - Minimal wrappers around application methods.
"""
from __future__ import annotations


class BackgroundWatchController:
    """Delegates background watch scheduling to the application."""

    def __init__(self, app) -> None:
        self.app = app

    def schedule(self, *, immediate: bool = False) -> None:
        self.app._schedule_background_watch(immediate=immediate)

    def cancel(self) -> None:
        self.app._cancel_background_watch()
