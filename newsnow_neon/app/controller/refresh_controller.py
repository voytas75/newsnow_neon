"""Refresh workflow controller.

Updates: v0.52 - 2025-11-18 - Added minimal delegation to preserve behavior.
"""
from __future__ import annotations

import threading
from typing import Optional


class RefreshController:
    """Encapsulates refresh trigger and background worker wiring."""

    def __init__(self, app) -> None:
        self.app = app

    def refresh(self, *, force_refresh: bool = False) -> None:
        """Trigger refresh preserving history/labels and non-blocking UI."""
        if getattr(self.app, "_history_mode", False):
            self.app._exit_history_mode(trigger_refresh=False)
        self.app._log_status("Fetching AI headlines…")
        if hasattr(self.app, "next_refresh_var"):
            self.app.next_refresh_var.set("Refreshing…")
        self.app._update_status_summary()
        threading.Thread(
            target=self.app._refresh_worker, args=(force_refresh,), daemon=True
        ).start()
