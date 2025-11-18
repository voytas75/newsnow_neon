"""Redis diagnostics controller.

Updates: v0.52 - 2025-11-18 - Minimal wrapper for meter updates.
"""
from __future__ import annotations
import logging
import tkinter as tk
from ...cache import get_redis_client
from ...config import REDIS_URL


class RedisController:
    """Handles Redis availability meter and diagnostics state."""

    def __init__(self, app) -> None:
        self.app = app

    def update_redis_meter(self) -> None:
        client = get_redis_client()
        if client is None:
            self.app.redis_meter_var.set("Redis: OFF")
            self.app.redis_meter_label.config(fg="#FF6B6B")
            if hasattr(self.app, "redis_stats_btn"):
                state = (
                    tk.DISABLED
                    if not REDIS_URL
                    else (
                        tk.DISABLED
                        if getattr(self.app, "_loading_redis_stats", False)
                        else tk.NORMAL
                    )
                )
                self.app.redis_stats_btn.config(state=state)
            self.app._refresh_history_controls_state()
            return

        try:
            client.ping()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - redis ping failure
            logging.getLogger(__name__).debug(
                "Redis ping failed; treating cache as unavailable: %s", exc
            )
            self.app.redis_meter_var.set("Redis: OFF")
            self.app.redis_meter_label.config(fg="#FF6B6B")
            if hasattr(self.app, "redis_stats_btn"):
                state = (
                    tk.DISABLED
                    if not REDIS_URL
                    else (
                        tk.DISABLED
                        if getattr(self.app, "_loading_redis_stats", False)
                        else tk.NORMAL
                    )
                )
                self.app.redis_stats_btn.config(state=state)
            self.app._refresh_history_controls_state()
            return

        self.app.redis_meter_var.set("Redis: ON")
        self.app.redis_meter_label.config(fg="#32CD32")
        if hasattr(self.app, "redis_stats_btn"):
            state = (
                tk.DISABLED
                if not REDIS_URL
                else (
                    tk.DISABLED
                    if getattr(self.app, "_loading_redis_stats", False)
                    else tk.NORMAL
                )
            )
            self.app.redis_stats_btn.config(state=state)
        self.app._refresh_history_controls_state()
