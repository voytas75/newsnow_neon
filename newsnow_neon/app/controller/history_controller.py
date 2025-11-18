"""HistoryController encapsulates history loading, activation, and exit.

Updates: v0.52 - 2025-11-18 - Introduce controller scaffold to move history
logic out of AINewsApp; initial delegation keeps UI callbacks in app.

This module is an incremental extraction: thread starting, service calls,
and scheduling are centralized here while UI updates still call back into
the application for now. Subsequent refactors will migrate UI mutations.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional, Sequence, TYPE_CHECKING

from tkinter import messagebox

from ...config import REDIS_URL
from ...cache import get_redis_client
from ...models import HistoricalSnapshot
from ..services import load_historical_snapshots

if TYPE_CHECKING:  # Avoid circular import at runtime
    # Forward-declare to appease type checkers; runtime uses duck-typing.
    from ...application import AINewsApp


logger = logging.getLogger(__name__)


class HistoryController:
    """Owns the workflow for history snapshots: load, activate, exit."""

    def __init__(self, app: "AINewsApp") -> None:
        """Bind to the Tk application orchestrator instance."""
        self.app = app

    # Public API (to be called from AINewsApp)

    def request_history_refresh(self) -> None:
        """Trigger a background task to load recent history snapshots.

        Performs gating checks (Redis, toggle state, connection) and,
        if permitted, starts a worker thread then updates initial UI state.
        """
        if getattr(self.app, "_loading_history", False):
            return

        if not REDIS_URL:
            messagebox.showinfo(
                "History unavailable",
                "Redis caching is disabled. Set REDIS_URL to browse history snapshots.",
            )
            return

        if not bool(self.app.historical_cache_var.get()):
            messagebox.showinfo(
                "History disabled",
                "Enable the 24h history toggle to start collecting historical snapshots.",
            )
            return

        if get_redis_client() is None:
            messagebox.showwarning(
                "History unavailable",
                "Redis connection is unavailable. Check the Redis URL and retry.",
            )
            return

        self.app._loading_history = True
        self.app.history_status_var.set("Loading history snapshots…")
        try:
            self.app.history_reload_btn.config(state=self._tk_state(False))
        except Exception:
            logger.debug("Unable to disable history refresh button before loading.")

        self.app.history_listbox.configure(state=self._tk_state(False))
        self.app.history_listbox_hover.hide()

        threading.Thread(target=self._history_loader_worker, daemon=True).start()

    def activate_history_selection(self, event: Optional[object] = None) -> Optional[str]:
        """Activate current listbox selection; delegate to app UI for now."""
        return self.app._activate_history_selection(event)

    def apply_history_snapshot(self, snapshot: HistoricalSnapshot) -> None:
        """Apply a specific snapshot; delegate UI updates to app for now."""
        self.app._apply_history_snapshot(snapshot)

    def exit_history_mode(self, *, trigger_refresh: bool = True) -> None:
        """Exit history mode; delegate workflow to app for now."""
        self.app._exit_history_mode(trigger_refresh=trigger_refresh)

    def restore_live_flow_state(self) -> tuple[bool, bool, bool]:
        """Restore live flow state; delegate to app for now."""
        return self.app._restore_live_flow_state()

    def format_history_entry(self, snapshot: HistoricalSnapshot) -> str:
        """Format history listbox label; reuse app formatting for now."""
        return self.app._format_history_entry(snapshot)

    def format_history_tooltip(self, snapshot: HistoricalSnapshot) -> str:
        """Format history tooltip text; reuse app formatting for now."""
        return self.app._format_history_tooltip(snapshot)

    def on_history_select(self, event: object) -> None:
        """Handle listbox selection; delegate to app for now."""
        self.app._on_history_select(event)  # type: ignore[no-any-return]

    def on_history_motion(self, event: object) -> None:
        """Handle hover motion; delegate tooltip behavior to app for now."""
        self.app._on_history_motion(event)

    # Internal worker and callback

    def _history_loader_worker(self) -> None:
        """Background worker to load history snapshots via services."""
        error: Optional[str] = None
        try:
            snapshots = load_historical_snapshots()
        except Exception as exc:  # defensive guard; keep app responsive
            logger.exception("Failed to load historical snapshots.")
            snapshots = []
            error = str(exc)

        # Marshal back onto Tk main thread
        self.app.after(0, lambda: self.handle_history_loaded(snapshots, error))

    def handle_history_loaded(
        self, snapshots: Sequence[HistoricalSnapshot], error: Optional[str]
    ) -> None:
        """Handle loaded snapshots and update UI state.

        For incremental extraction, reuse the app's existing UI handler.
        """
        self.app._handle_history_loaded(snapshots, error)

    # Helpers

    @staticmethod
    def _tk_state(enabled: bool) -> str:
        """Return Tk state flag string for widgets."""
        return "normal" if enabled else "disabled"


__all__ = ["HistoryController"]