"""History UI helpers extracted from the application controller.

Updates: v0.53 - 2025-11-18 - Moved history list rendering and mode
handling out of application.py to reduce controller size.
"""
from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from typing import Optional, Sequence, Tuple

from ..services import build_ticker_text
from ..helpers.app_helpers import format_history_entry, format_history_tooltip
from ...config import REDIS_URL
from ...models import HistoricalSnapshot, LiveFlowState

logger = logging.getLogger(__name__)


def handle_history_loaded(
    app: tk.Tk, snapshots: Sequence[HistoricalSnapshot], error: Optional[str]
) -> None:
    """Populate history listbox and status after load completes."""
    app._loading_history = False
    can_refresh = bool(REDIS_URL) and bool(app.historical_cache_var.get())
    try:
        app.history_reload_btn.config(state=tk.NORMAL if can_refresh else tk.DISABLED)
    except Exception:
        logger.debug("Unable to update history refresh button state.")

    app.history_listbox.configure(state=tk.NORMAL)
    app.history_listbox.delete(0, tk.END)
    app._history_entries = list(snapshots)

    if error:
        app.history_status_var.set(f"History load failed: {error}")
        app.history_listbox.insert(tk.END, "Unable to load history snapshots right now.")
        app.history_listbox.configure(state=tk.DISABLED)
        return

    if not app._history_entries:
        message = "No cached headlines captured in the last 24 hours."
        app.history_status_var.set(message)
        app.history_listbox.insert(tk.END, message)
        app.history_listbox.configure(state=tk.DISABLED)
        app.history_listbox_hover.hide()
        if app._history_mode:
            exit_history_mode(app, trigger_refresh=False)
        return

    app.history_listbox.configure(state=tk.NORMAL)
    for snapshot in app._history_entries:
        app.history_listbox.insert(
            tk.END, format_history_entry(snapshot, app._timezone, app._timezone_name)
        )
    app.history_status_var.set(
        f"{len(app._history_entries)} snapshots loaded (newest first). Select to view."
    )
    app.history_listbox.selection_clear(0, tk.END)
    app.history_listbox_hover.hide()

    if app._history_mode and app._history_active_snapshot is not None:
        active_key = app._history_active_snapshot.key
        keys = [entry.key for entry in app._history_entries]
        if active_key not in keys:
            exit_history_mode(app, trigger_refresh=False)
        else:
            index = keys.index(active_key)
            app.history_listbox.selection_set(index)
            app.history_listbox.see(index)

    refresh_history_controls_state(app)


def on_history_select(app: tk.Tk, _event: tk.Event) -> None:
    """Handle selection change in history listbox."""
    if app.history_listbox.cget("state") != tk.NORMAL:
        return
    activate_history_selection(app)


def activate_history_selection(
    app: tk.Tk, _event: Optional[tk.Event] = None
) -> Optional[str]:
    """Activate the currently selected snapshot in history listbox."""
    if app.history_listbox.cget("state") != tk.NORMAL:
        return "break" if _event is not None else None
    selection = app.history_listbox.curselection()
    if not selection:
        return "break" if _event is not None else None
    index = selection[0]
    if index < 0 or index >= len(app._history_entries):
        return "break" if _event is not None else None
    snapshot = app._history_entries[index]
    apply_history_snapshot(app, snapshot)
    return "break" if _event is not None else None


def on_history_motion(app: tk.Tk, event: tk.Event) -> None:
    """Show a tooltip preview for the snapshot under mouse."""
    if app.history_listbox.cget("state") != tk.NORMAL:
        app.history_listbox_hover.hide()
        return
    if not app._history_entries:
        app.history_listbox_hover.hide()
        return
    index = app.history_listbox.nearest(event.y)
    if index < 0 or index >= len(app._history_entries):
        app.history_listbox_hover.hide()
        return
    snapshot = app._history_entries[index]
    tooltip = format_history_tooltip(snapshot, app._timezone, app._timezone_name)
    app.history_listbox_hover.show(tooltip, event.x_root, event.y_root)


def capture_live_flow_state(app: tk.Tk) -> LiveFlowState:
    """Capture view/selection and timers to restore after exiting history."""
    listbox_view_top: Optional[float] = None
    try:
        view = app.listbox.yview()
    except Exception:
        view = None
    if view:
        listbox_view_top = float(view[0])

    selection_index = app._selected_line

    return LiveFlowState(
        next_refresh_time=app._next_refresh_time,
        auto_refresh_enabled=bool(app.auto_refresh_var.get()),
        background_watch_enabled=bool(app.background_watch_var.get()),
        background_watch_next_run=app._background_watch_next_run,
        pending_new_headlines=app._pending_new_headlines,
        last_reported_pending=app._last_reported_pending,
        background_candidate_keys=frozenset(app._background_candidate_keys),
        listbox_view_top=listbox_view_top,
        listbox_selection=selection_index,
    )


def apply_history_snapshot(app: tk.Tk, snapshot: HistoricalSnapshot) -> None:
    """Switch UI into history mode and render the selected snapshot."""
    app.history_listbox_hover.hide()
    app._ensure_options_visible()
    if not app._history_mode:
        raw_headlines = list(app._raw_headlines) if app._raw_headlines else list(app.headlines)
        app._last_live_payload = (
            raw_headlines,
            app._current_ticker_text,
            app._last_headline_from_cache,
        )
        app._last_live_flow_state = capture_live_flow_state(app)
    app._history_mode = True
    app._history_active_snapshot = snapshot
    app.exit_history_btn.config(state=tk.NORMAL)
    ticker_text = snapshot.cache.ticker_text or build_ticker_text(snapshot.cache.headlines)
    app.history_status_var.set(
        f"History mode: {format_history_entry(snapshot, app._timezone, app._timezone_name)}"
    )
    app._log_status(
        f"Viewing historical snapshot captured at {snapshot.captured_at.isoformat()}."
    )
    app._cancel_pending_refresh_jobs()
    app._next_refresh_time = None
    app.next_refresh_var.set("Next refresh: history view")
    app._update_content(
        headlines=list(snapshot.cache.headlines),
        ticker_text=ticker_text,
        from_cache=True,
        reschedule=False,
        log_status=False,
        update_tickers=False,
    )
    app._log_status(
        f"Loaded {snapshot.headline_count} cached headlines captured at {snapshot.captured_at.isoformat()}."
    )
    try:
        app._clear_listbox_selection()
        app.listbox.yview_moveto(0.0)
    except Exception:
        logger.debug("Unable to reset main listbox selection after history load.")


def restore_live_flow_state(app: tk.Tk) -> Tuple[bool, bool, bool]:
    """Restore auto/background timers and listbox state after history."""
    snapshot = app._last_live_flow_state
    if snapshot is None:
        return False, False, False
    app._last_live_flow_state = None

    app._pending_new_headlines = snapshot.pending_new_headlines
    app._last_reported_pending = snapshot.last_reported_pending
    app._background_candidate_keys = set(snapshot.background_candidate_keys)
    app._update_background_watch_label()

    if snapshot.listbox_selection is not None:
        try:
            app._select_listbox_line(snapshot.listbox_selection)
            app.listbox.see(f"{snapshot.listbox_selection}.0")
        except Exception:
            logger.debug("Unable to restore listbox selection from live state.")
    if snapshot.listbox_view_top is not None:
        try:
            app.listbox.yview_moveto(snapshot.listbox_view_top)
        except Exception:
            logger.debug("Unable to restore listbox scroll position from live state.")

    auto_scheduled = False
    background_scheduled = False
    refresh_triggered = False
    auto_enabled_now = bool(app.auto_refresh_var.get())

    if not auto_enabled_now:
        app._schedule_auto_refresh()
        auto_scheduled = True
    elif snapshot.auto_refresh_enabled and snapshot.next_refresh_time is not None:
        remaining_ms = int(
            (snapshot.next_refresh_time - datetime.now()).total_seconds() * 1000
        )
        if remaining_ms <= 0:
            app.refresh_headlines(force_refresh=True)
            refresh_triggered = True
        else:
            app._schedule_auto_refresh_with_delay(remaining_ms)
        auto_scheduled = True
    else:
        app._schedule_auto_refresh()
        auto_scheduled = True

    background_enabled_now = bool(app.background_watch_var.get())
    if not background_enabled_now:
        app._cancel_background_watch()
        app._background_watch_next_run = None
        app._update_background_watch_label()
        background_scheduled = True
    elif snapshot.background_watch_enabled and snapshot.background_watch_next_run is not None:
        delay_ms = int(
            (snapshot.background_watch_next_run - datetime.now()).total_seconds() * 1000
        )
        if delay_ms <= 0:
            app._schedule_background_watch_with_delay(0)
        else:
            app._schedule_background_watch_with_delay(delay_ms)
        background_scheduled = True
    else:
        app._schedule_background_watch()
        background_scheduled = True

    return auto_scheduled, background_scheduled, refresh_triggered


def exit_history_mode(app: tk.Tk, *, trigger_refresh: bool = True) -> None:
    """Exit history mode and restore prior state."""
    if not app._history_mode:
        return
    app._history_mode = False
    app._history_active_snapshot = None
    app.exit_history_btn.config(state=tk.DISABLED)
    app.history_listbox.selection_clear(0, tk.END)
    app.history_listbox_hover.hide()
    if app._history_entries:
        app.history_status_var.set(
            f"{len(app._history_entries)} snapshots loaded (newest first). Select to view."
        )
    else:
        app.history_status_var.set("History mode off — refresh to browse cached snapshots.")

    restored = False
    if app._last_live_payload:
        raw_headlines, ticker_text, from_cache = app._last_live_payload
        app._last_live_payload = None
        app._update_content(
            headlines=list(raw_headlines),
            ticker_text=ticker_text,
            from_cache=from_cache,
            reschedule=False,
            log_status=False,
            update_tickers=False,
        )
        restored = True

    auto_restored, background_restored, refresh_triggered = restore_live_flow_state(app)

    if not restored and trigger_refresh and not refresh_triggered:
        app.refresh_headlines(force_refresh=False)

    if not restored:
        app._restore_live_tickers()
    if not auto_restored:
        app._schedule_auto_refresh()
    if not background_restored:
        app._schedule_background_watch(immediate=True)
    refresh_history_controls_state(app)


def refresh_history_controls_state(app: tk.Tk) -> None:
    """Enable/disable history controls based on settings and data state."""
    history_enabled = bool(app.historical_cache_var.get())
    redis_enabled = bool(REDIS_URL)
    can_refresh = history_enabled and redis_enabled
    try:
        app.history_reload_btn.config(state=tk.NORMAL if can_refresh else tk.DISABLED)
    except Exception:
        logger.debug("Unable to update history reload button state.")

    if not can_refresh:
        exit_history_mode(app, trigger_refresh=False)
        placeholder = (
            "History unavailable — Redis disabled." if not redis_enabled
            else "History disabled. Enable the 24h history toggle to collect snapshots."
        )
        app.history_listbox.configure(state=tk.DISABLED)
        app.history_listbox.delete(0, tk.END)
        app.history_listbox.insert(tk.END, placeholder)
        app.history_status_var.set(placeholder)
        return

    if app._history_entries:
        if not app._history_mode:
            app.history_status_var.set(
                f"{len(app._history_entries)} snapshots loaded (newest first). Select to view."
            )
        app.history_listbox.configure(state=tk.NORMAL)
    else:
        app.history_listbox.configure(state=tk.DISABLED)
        app.history_listbox.delete(0, tk.END)
        app.history_listbox.insert(
            tk.END, "History snapshots appear here when loaded."
        )
        if not app._history_mode:
            app.history_status_var.set(
                "History mode off — refresh to browse cached snapshots."
            )


__all__ = [
    "handle_history_loaded",
    "on_history_select",
    "activate_history_selection",
    "on_history_motion",
    "capture_live_flow_state",
    "apply_history_snapshot",
    "restore_live_flow_state",
    "exit_history_mode",
    "refresh_history_controls_state",
]