"""Background watch controller for NewsNow Neon.

Updates: v0.52 - 2025-11-18 - Extracted background watch scheduling and
trigger workflow into controller stub to reduce application.py size while
preserving behavior.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from typing import List, Optional, TYPE_CHECKING

from ...config import (
    BACKGROUND_WATCH_INITIAL_DELAY_MS,
    BACKGROUND_WATCH_INTERVAL_MS,
)
from ...models import Headline
from ...app.services import fetch_headlines

logger = logging.getLogger(__name__)


class BackgroundWatchController:
    """Manages background watch scheduling and trigger workflow.

    This controller encapsulates the scheduling of background headline
    checks, spawning a worker thread, and delegating success/failure
    handling back to the application to preserve current UI behavior.
    """

    def __init__(self, app: "AINewsApp") -> None:
        self.app = app

    def cancel(self) -> None:
        """Cancel any scheduled background watch run."""
        job = getattr(self.app, "_background_watch_job", None)
        if job is not None:
            try:
                self.app.after_cancel(job)
            except Exception:
                pass
            self.app._background_watch_job = None
        self.app._background_watch_next_run = None

    def schedule(self, *, immediate: bool = False) -> None:
        """Schedule background watch using configured default delays."""
        self.cancel()
        enabled = bool(self.app.background_watch_var.get())
        if not enabled:
            self.app._background_watch_next_run = None
            return

        delay = (
            BACKGROUND_WATCH_INITIAL_DELAY_MS if immediate else BACKGROUND_WATCH_INTERVAL_MS
        )
        if delay <= 0:
            delay = BACKGROUND_WATCH_INTERVAL_MS

        self.app._background_watch_next_run = datetime.now() + timedelta(
            milliseconds=delay
        )
        self.app._background_watch_job = self.app.after(delay, self._trigger)

    def schedule_with_delay(self, delay_ms: int) -> None:
        """Schedule background watch with an explicit millisecond delay."""
        self.cancel()
        enabled = bool(self.app.background_watch_var.get())
        if not enabled:
            self.app._background_watch_next_run = None
            return

        delay = max(0, int(delay_ms))
        if delay == 0:
            self.app._background_watch_next_run = datetime.now()
            self.app._background_watch_job = self.app.after_idle(self._trigger)
        else:
            self.app._background_watch_next_run = datetime.now() + timedelta(
                milliseconds=delay
            )
            self.app._background_watch_job = self.app.after(delay, self._trigger)

    def _trigger(self) -> None:
        """Entry point invoked by Tk 'after' to run background watch."""
        self.app._background_watch_next_run = None
        self.app._background_watch_job = None

        enabled = bool(self.app.background_watch_var.get())
        if not enabled:
            # Clear counters in app for consistency
            self.app._pending_new_headlines = 0
            self.app._last_reported_pending = 0
            self.app._background_candidate_keys.clear()
            self.app._update_background_watch_label()
            return

        if getattr(self.app, "_background_watch_running", False):
            # Already running; simply reschedule.
            self.schedule()
            return

        if getattr(self.app, "_history_mode", False):
            # Do not poll while browsing history.
            self.schedule()
            return

        self.app._background_watch_running = True
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        """Execute background check in a thread and marshal result to UI."""
        try:
            headlines, _from_cache, _ticker = fetch_headlines(force_refresh=True)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.debug("Background watch fetch failed: %s", exc)
            self.app.after(0, self._handle_failure)
            return

        self.app.after(0, lambda: self._handle_success(headlines))

    def _handle_failure(self) -> None:
        """Delegate failure handling to the application and reschedule."""
        self.app._background_watch_running = False
        # Preserve existing behavior:
        if hasattr(self.app, "_handle_background_watch_failure"):
            self.app._handle_background_watch_failure()
        else:
            # Minimal fallback: reschedule when enabled
            if bool(self.app.background_watch_var.get()):
                self.schedule()

    def _handle_success(self, headlines: List[Headline]) -> None:
        """Delegate success handling to the application and reschedule."""
        self.app._background_watch_running = False
        if not bool(self.app.background_watch_var.get()):
            self.app._pending_new_headlines = 0
            self.app._last_reported_pending = 0
            self.app._update_background_watch_label()
            return

        if getattr(self.app, "_history_mode", False):
            self.schedule()
            return

        # Preserve existing calculation/UI update via app hook
        if hasattr(self.app, "_handle_background_watch_result"):
            self.app._handle_background_watch_result(headlines)
        else:
            # If hook is missing, simply log and reschedule.
            logger.info(
                "Background watch fetched %s headline(s). Wiring pending.",
                len(headlines),
            )

        # Reschedule continuous background watch
        self.schedule()