"""Settings controller.

Updates: v0.52 - 2025-11-18 - Minimal wrappers for settings application.
"""
from __future__ import annotations


class SettingsController:
    """Delegates settings-related operations to the application."""

    def __init__(self, app) -> None:
        self.app = app

    def update_status_summary(self) -> None:
        self.app._update_status_summary()

    def apply_timezone_selection(self, value: str) -> None:
        self.app._apply_timezone_selection(value, persist=True)
