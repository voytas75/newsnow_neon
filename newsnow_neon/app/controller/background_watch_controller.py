"""Background watch controller.

Updates:
- v0.52 - 2025-11-18 - Minimal wrappers around application methods.
- v0.52.2 - 2025-11-18 - Moved background watch workflow and state handling here.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from typing import Any, List, Optional, Set, Tuple

from ...config import (
    BACKGROUND_WATCH_INTERVAL_MS,
    BACKGROUND_WATCH_INITIAL_DELAY_MS,
)
from ...models import Headline
from ...app.services import fetch_headlines


logger = logging.getLogger(__name__)


class BackgroundWatchController:
    """Handles scheduling, detection, and auto-refresh triggers for background watch."""

    def __init__(self, app) -> None:
        self.app = app

    # Scheduling API

    def schedule(self, *, immediate: bool = False) -> None:
        """Schedule the next background watch run; computes delay and registers Tk job."""
        self.cancel()
        if not bool(self.app.background_watch_var.get()):
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
        self.app._background_watch_job = self.app.after(delay, self.trigger)

    def schedule_with_delay(self, delay_ms: int) -> None:
        """Schedule with an explicit delay in milliseconds."""
        self.cancel()
        if not bool(self.app.background_watch_var.get()):
            self.app._background_watch_next_run = None
            return
        delay = max(0, int(delay_ms))
        if delay == 0:
            self.app._background_watch_next_run = datetime.now()
            self.app._background_watch_job = self.app.after_idle(self.trigger)
        else:
            self.app._background_watch_next_run = datetime.now() + timedelta(
                milliseconds=delay
            )
            self.app._background_watch_job = self.app.after(delay, self.trigger)

    def cancel(self) -> None:
        """Cancel any pending background watch job."""
        if getattr(self.app, "_background_watch_job", None) is not None:
            try:
                self.app.after_cancel(self.app._background_watch_job)
            except Exception:
                pass
            self.app._background_watch_job = None
        self.app._background_watch_next_run = None

    # Execution

    def trigger(self) -> None:
        """Entry point when the scheduled job fires."""
        self.app._background_watch_next_run = None
        self.app._background_watch_job = None
        if not bool(self.app.background_watch_var.get()):
            return
        if getattr(self.app, "_background_watch_running", False):
            self.schedule()
            return
        if getattr(self.app, "_history_mode", False):
            self.schedule()
            return
        self.app._background_watch_running = True
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self) -> None:
        """Fetch headlines in background and dispatch result on main thread."""
        try:
            headlines, _from_cache, _ticker = fetch_headlines(force_refresh=True)
        except Exception as exc:  # pragma: no cover - network failures
            logger.debug("Background watch fetch failed: %s", exc)
            self.app.after(0, self.handle_failure)
            return
        self.app.after(0, lambda: self.handle_result(headlines))

    def handle_failure(self) -> None:
        """Finalize failure; re-schedule if still enabled."""
        self.app._background_watch_running = False
        if bool(self.app.background_watch_var.get()):
            self.schedule()

    def handle_result(self, headlines: List[Headline]) -> None:
        """Compute pending unseen headlines; update label; maybe auto-refresh; reschedule."""
        self.app._background_watch_running = False
        if not bool(self.app.background_watch_var.get()):
            self.app._pending_new_headlines = 0
            self.app._last_reported_pending = 0
            self.update_label()
            return
        if getattr(self.app, "_history_mode", False):
            self.schedule()
            return

        filtered = self.app._filter_headlines(headlines)
        current_keys: Set[Tuple[str, str]] = {
            self.app._headline_key(headline) for _, headline in self.app._filtered_entries()
        }
        candidate_keys: Set[Tuple[str, str]] = {
            self.app._headline_key(headline)
            for headline in filtered
            if self.app._matches_filters(headline)
        }

        self.app._background_candidate_keys = candidate_keys
        pending = len(candidate_keys.difference(current_keys))
        self.app._pending_new_headlines = pending

        if pending != self.app._last_reported_pending:
            if pending > 0:
                logger.info("Background watch detected %s unseen headline(s).", pending)
            elif self.app._last_reported_pending > 0:
                logger.info("Background watch count cleared after refresh.")
            self.app._last_reported_pending = pending

        self.update_label()
        self.maybe_auto_refresh_for_pending()
        self.schedule()

    # UI helpers

    def update_label(self) -> None:
        """Update the background watch label and status summary."""
        if not hasattr(self.app, "new_headlines_var"):
            return
        enabled = bool(self.app.background_watch_var.get())
        if not enabled:
            self.app.new_headlines_var.set("Background watch: off")
            if hasattr(self.app, "new_headlines_label"):
                self.app.new_headlines_label.config(fg="lightgray")
            return

        count = max(0, int(self.app._pending_new_headlines))
        if count > 0:
            self.app.new_headlines_var.set(f"New headlines pending: {count}")
            if hasattr(self.app, "new_headlines_label"):
                self.app.new_headlines_label.config(fg="#FFD54F")
        else:
            self.app.new_headlines_var.set("New headlines pending: 0")
            if hasattr(self.app, "new_headlines_label"):
                self.app.new_headlines_label.config(fg="#89CFF0")
        self.app._update_status_summary()

    # Threshold helpers

    def coerce_threshold(self, value: Any) -> int:
        """Clamp threshold to [1, 999] and return numeric value."""
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            numeric = self.app.settings.get(
                "background_watch_refresh_threshold",  # fallback
                1,
            )
        return max(1, min(999, numeric))

    def apply_threshold(self) -> None:
        """Apply threshold from spinbox var, persist, and check for auto-refresh."""
        threshold = self.coerce_threshold(self.app.background_watch_threshold_var.get())
        if threshold != self.app.background_watch_threshold_var.get():
            self.app.background_watch_threshold_var.set(threshold)
        if threshold == getattr(self.app, "_background_refresh_threshold", threshold):
            return
        self.app._background_refresh_threshold = threshold
        self.app.settings["background_watch_refresh_threshold"] = threshold
        self.app._save_settings()
        self.maybe_auto_refresh_for_pending()

    def recompute_pending(self) -> None:
        """Recompute pending count using existing candidate set and current view."""
        if not bool(self.app.background_watch_var.get()):
            return
        if not getattr(self.app, "_background_candidate_keys", None):
            return
        current_keys = {
            self.app._headline_key(headline) for _, headline in self.app._filtered_entries()
        }
        pending = len(self.app._background_candidate_keys.difference(current_keys))
        if pending == self.app._pending_new_headlines:
            return
        self.app._pending_new_headlines = pending
        self.app._last_reported_pending = pending
        self.update_label()
        self.maybe_auto_refresh_for_pending()

    def maybe_auto_refresh_for_pending(self) -> None:
        """Trigger auto refresh if pending unseen count crosses threshold."""
        if not bool(self.app.background_watch_var.get()):
            return
        if getattr(self.app, "_history_mode", False):
            return
        threshold = max(1, int(self.app._background_refresh_threshold))
        if self.app._pending_new_headlines < threshold:
            return
        if getattr(self.app, "_background_watch_running", False):
            return
        if getattr(self.app, "_refresh_job", None) is not None:
            self.app._cancel_pending_refresh_jobs()
            self.app._next_refresh_time = None

        self.app._log_status(
            f"Auto-refreshing for {self.app._pending_new_headlines} unseen headline(s)."
        )
        logger.info(
            "Triggering auto refresh after reaching unseen headline threshold (%s).",
            self.app._pending_new_headlines,
        )
        self.app._pending_new_headlines = 0
        self.app._last_reported_pending = 0
        self.app._background_candidate_keys.clear()
        self.update_label()
        self.app.refresh_headlines(force_refresh=True)
