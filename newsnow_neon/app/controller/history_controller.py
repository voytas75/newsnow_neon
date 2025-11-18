"""History controller.

Updates:
- v0.52 - 2025-11-18 - Minimal wrappers for history workflows.
- v0.52.1 - 2025-11-18 - Moved history refresh, loading, formatting, and UI
  interactions from application.py into controller to reduce orchestrator size.
"""
from __future__ import annotations

import threading
from typing import Optional, Sequence
import tkinter as tk
from tkinter import messagebox

from ...cache import get_redis_client
from ...config import REDIS_URL
from ...app.services import load_historical_snapshots
from ...models import HistoricalSnapshot  # type: ignore


class HistoryController:
    """Encapsulates history interactions and UI updates."""

    def __init__(self, app) -> None:
        self.app = app

    def request_refresh(self) -> None:
        """Start loading history snapshots with guards and UI state updates."""
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
        self.app.history_reload_btn.config(state=tk.DISABLED)
        self.app.history_listbox.configure(state=tk.DISABLED)
        self.app.history_listbox_hover.hide()
        threading.Thread(target=self.load_history_worker, daemon=True).start()

    def load_history_worker(self) -> None:
        """Background worker to fetch snapshots and return to main thread."""
        error: Optional[str] = None
        try:
            snapshots = load_historical_snapshots()
        except Exception as exc:  # pragma: no cover - defensive guard
            tk_logger = getattr(self.app, "logger", None)
            # Use module-level logging via app to keep behavior similar
            import logging

            logging.getLogger(__name__).exception("Failed to load historical snapshots.")
            snapshots = []
            error = str(exc)
        self.app.after(0, lambda: self.handle_history_loaded(snapshots, error))

    def handle_history_loaded(
        self, snapshots: Sequence[HistoricalSnapshot], error: Optional[str]
    ) -> None:
        """Update UI state after loading snapshots and maintain selection."""
        self.app._loading_history = False
        can_refresh = bool(REDIS_URL) and bool(self.app.historical_cache_var.get())
        try:
            self.app.history_reload_btn.config(
                state=tk.NORMAL if can_refresh else tk.DISABLED
            )
        except Exception:
            import logging

            logging.getLogger(__name__).debug(
                "Unable to update history refresh button state."
            )

        self.app.history_listbox.configure(state=tk.NORMAL)
        self.app.history_listbox.delete(0, tk.END)
        self.app._history_entries = list(snapshots)

        if error:
            self.app.history_status_var.set(f"History load failed: {error}")
            self.app.history_listbox.insert(
                tk.END, "Unable to load history snapshots right now."
            )
            self.app.history_listbox.configure(state=tk.DISABLED)
            return

        if not self.app._history_entries:
            message = "No cached headlines captured in the last 24 hours."
            self.app.history_status_var.set(message)
            self.app.history_listbox.insert(tk.END, message)
            self.app.history_listbox.configure(state=tk.DISABLED)
            self.app.history_listbox_hover.hide()
            if getattr(self.app, "_history_mode", False):
                self.app._exit_history_mode(trigger_refresh=False)
            return

        self.app.history_listbox.configure(state=tk.NORMAL)
        for snapshot in self.app._history_entries:
            self.app.history_listbox.insert(tk.END, self.format_entry(snapshot))
        self.app.history_status_var.set(
            f"{len(self.app._history_entries)} snapshots loaded (newest first). Select to view."
        )
        self.app.history_listbox.selection_clear(0, tk.END)
        self.app.history_listbox_hover.hide()

        if getattr(self.app, "_history_mode", False) and (
            getattr(self.app, "_history_active_snapshot", None) is not None
        ):
            active_key = self.app._history_active_snapshot.key
            keys = [entry.key for entry in self.app._history_entries]
            if active_key not in keys:
                self.app._exit_history_mode(trigger_refresh=False)
            else:
                index = keys.index(active_key)
                self.app.history_listbox.selection_set(index)
                self.app.history_listbox.see(index)

        self.app._refresh_history_controls_state()

    def format_entry(self, snapshot: HistoricalSnapshot) -> str:
        """Human-friendly single-line label for a snapshot."""
        local_dt = snapshot.captured_at.astimezone(self.app._timezone)
        tz_label = local_dt.tzname() or self.app._timezone_name
        timestamp = local_dt.strftime("%Y-%m-%d %H:%M")
        headline_label = "headline" if snapshot.headline_count == 1 else "headlines"
        return f"{timestamp} {tz_label} • {snapshot.headline_count} {headline_label}"

    def format_tooltip(self, snapshot: HistoricalSnapshot) -> str:
        """Multi-line tooltip with details and ticker preview."""
        local_dt = snapshot.captured_at.astimezone(self.app._timezone)
        tz_label = local_dt.tzname() or self.app._timezone_name
        lines = [
            f"Captured: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_label}",
            f"Redis key: {snapshot.key}",
            f"Headlines: {snapshot.headline_count}",
        ]
        if snapshot.summary_count:
            lines.append(f"Summaries: {snapshot.summary_count}")
        ticker_preview = snapshot.cache.ticker_text or ""
        if ticker_preview:
            truncated = (
                ticker_preview
                if len(ticker_preview) <= 120
                else ticker_preview[:117].rstrip() + "…"
            )
            lines.append(f"Ticker: {truncated}")
        return "\n".join(lines)

    def on_select(self, _event: tk.Event) -> None:
        """Handle listbox select event when enabled."""
        if self.app.history_listbox.cget("state") != tk.NORMAL:
            return
        self.activate_history_selection()

    def activate_history_selection(
        self, _event: Optional[tk.Event] = None
    ) -> Optional[str]:
        """Activate the currently selected snapshot."""
        if self.app.history_listbox.cget("state") != tk.NORMAL:
            return "break" if _event is not None else None
        selection = self.app.history_listbox.curselection()
        if not selection:
            return "break" if _event is not None else None
        index = selection[0]
        if index < 0 or index >= len(self.app._history_entries):
            return "break" if _event is not None else None
        snapshot = self.app._history_entries[index]
        self.app._apply_history_snapshot(snapshot)
        return "break" if _event is not None else None

    def on_motion(self, event: tk.Event) -> None:
        """Update tooltip when hovering history list entries."""
        if self.app.history_listbox.cget("state") != tk.NORMAL:
            self.app.history_listbox_hover.hide()
            return
        if not self.app._history_entries:
            self.app.history_listbox_hover.hide()
            return
        index = self.app.history_listbox.nearest(event.y)
        if index < 0 or index >= len(self.app._history_entries):
            self.app.history_listbox_hover.hide()
            return
        snapshot = self.app._history_entries[index]
        tooltip = self.format_tooltip(snapshot)
        self.app.history_listbox_hover.show(tooltip, event.x_root, event.y_root)

    def apply_snapshot(self, snapshot: "HistoricalSnapshot") -> None:
        """Apply a given snapshot to the application view."""
        self.app._apply_history_snapshot(snapshot)
