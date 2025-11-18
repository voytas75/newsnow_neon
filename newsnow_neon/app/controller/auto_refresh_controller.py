"""Auto-refresh scheduling controller.

Updates: v0.52 - 2025-11-18 - Minimal wrappers around application methods.
Updates: v0.52.1 - 2025-11-18 - Added cancel_pending_jobs to decouple from app.
"""
from __future__ import annotations


class AutoRefreshController:
    """Delegates auto-refresh scheduling and cancellation."""

    def __init__(self, app) -> None:
        self.app = app

    def schedule(self) -> None:
        """Schedule the next auto refresh based on current settings."""
        self.app._schedule_auto_refresh()

    def schedule_with_delay(self, delay_ms: int) -> None:
        """Schedule auto refresh with an explicit delay in milliseconds."""
        self.app._schedule_auto_refresh_with_delay(delay_ms)

    def cancel_pending_jobs(self) -> None:
        """Cancel any pending refresh and countdown jobs safely."""
        if getattr(self.app, "_refresh_job", None) is not None:
            try:
                self.app.after_cancel(self.app._refresh_job)
            except Exception:
                pass
            self.app._refresh_job = None

        if getattr(self.app, "_countdown_job", None) is not None:
            try:
                self.app.after_cancel(self.app._countdown_job)
            except Exception:
                pass
            self.app._countdown_job = None
