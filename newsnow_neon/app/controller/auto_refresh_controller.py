"""Auto refresh controller for NewsNow Neon.

Updates: v0.52 - 2025-11-18 - Extracted auto refresh scheduling into
controller stub.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class AutoRefreshController:
    """Manages auto refresh timing and countdown for the Tkinter app.

    Updates: v0.52 - 2025-11-18 - Extracted auto refresh scheduling into
    controller stub.
    """

    def __init__(self, app: "AINewsApp") -> None:
        self.app = app

    def cancel_pending_jobs(self) -> None:
        """Cancel scheduled refresh and countdown jobs if present."""
        refresh_job = getattr(self.app, "_refresh_job", None)
        if refresh_job is not None:
            try:
                self.app.after_cancel(refresh_job)
            except Exception:
                pass
            self.app._refresh_job = None

        countdown_job = getattr(self.app, "_countdown_job", None)
        if countdown_job is not None:
            try:
                self.app.after_cancel(countdown_job)
            except Exception:
                pass
            self.app._countdown_job = None

    def schedule(self) -> None:
        """Schedule the next auto refresh and start countdown."""
        self.cancel_pending_jobs()
        if getattr(self.app, "_history_mode", False):
            self.app._next_refresh_time = None
            self.app.next_refresh_var.set("Next refresh: history view")
            return

        auto_enabled = bool(self.app.auto_refresh_var.get())
        if not auto_enabled:
            self.app._next_refresh_time = None
            self.app.next_refresh_var.set("Next refresh: paused")
        else:
            interval_ms = self.app._auto_refresh_interval_ms()
            self.app.refresh_interval = interval_ms
            self.app._next_refresh_time = (
                datetime.now() + timedelta(milliseconds=interval_ms)
            )
            self.app._refresh_job = self.app.after(
                interval_ms, self._auto_refresh_trigger
            )

        self._start_refresh_countdown()
        self.app._update_status_summary()

    def schedule_with_delay(self, delay_ms: int) -> None:
        """Schedule auto refresh with a specific delay in milliseconds."""
        delay = max(0, int(delay_ms))
        self.cancel_pending_jobs()

        if getattr(self.app, "_history_mode", False):
            self.app._next_refresh_time = None
            self.app.next_refresh_var.set("Next refresh: history view")
            return

        if not bool(self.app.auto_refresh_var.get()):
            self.app._next_refresh_time = None
            self.app.next_refresh_var.set("Next refresh: paused")
            self._start_refresh_countdown()
            return

        interval_ms = self.app._auto_refresh_interval_ms()
        self.app.refresh_interval = interval_ms
        if delay == 0:
            self.app._next_refresh_time = datetime.now()
            self.app._refresh_job = self.app.after_idle(self._auto_refresh_trigger)
        else:
            self.app._next_refresh_time = (
                datetime.now() + timedelta(milliseconds=delay)
            )
            self.app._refresh_job = self.app.after(delay, self._auto_refresh_trigger)

        self._start_refresh_countdown()
        self.app._update_status_summary()

    def _auto_refresh_trigger(self) -> None:
        """Trigger an immediate refresh."""
        self.app._refresh_job = None
        self.app.refresh_headlines(force_refresh=True)

    def _start_refresh_countdown(self) -> None:
        """Start tick updates for the countdown label."""
        countdown_job = getattr(self.app, "_countdown_job", None)
        if countdown_job is not None:
            try:
                self.app.after_cancel(countdown_job)
            except Exception:
                pass
        self.app._countdown_job = self.app.after(0, self._tick_refresh_countdown)

    def _update_last_refresh_label(self) -> None:
        """Update the 'last refresh' status label."""
        last = getattr(self.app, "_last_refresh_time", None)
        if last is None:
            self.app.last_refresh_var.set("Last refresh: pending")
            return

        elapsed = datetime.now() - last
        seconds = max(0, int(elapsed.total_seconds()))
        if seconds < 60:
            label = f"{seconds}s ago"
        elif seconds < 3600:
            minutes, sec = divmod(seconds, 60)
            label = f"{minutes}m {sec:02d}s ago"
        else:
            hours, rem = divmod(seconds, 3600)
            minutes, sec = divmod(rem, 60)
            label = f"{hours}h {minutes:02d}m {sec:02d}s ago"

        self.app.last_refresh_var.set(f"Last refresh: {label}")
        self.app._update_status_summary()

    def _tick_refresh_countdown(self) -> None:
        """Update the 'next refresh' countdown every second."""
        auto_enabled = bool(self.app.auto_refresh_var.get())
        if getattr(self.app, "_history_mode", False):
            self.app.next_refresh_var.set("Next refresh: history view")
        elif not auto_enabled or self.app._next_refresh_time is None:
            self.app.next_refresh_var.set("Next refresh: paused")
        else:
            remaining = int(
                (self.app._next_refresh_time - datetime.now()).total_seconds()
            )
            if remaining <= 0:
                self.app.next_refresh_var.set("Next refresh: 00:00")
            else:
                minutes, seconds = divmod(remaining, 60)
                self.app.next_refresh_var.set(
                    f"Next refresh: {minutes:02d}:{seconds:02d}"
                )

        self._update_last_refresh_label()
        self.app._countdown_job = self.app.after(1000, self._tick_refresh_countdown)