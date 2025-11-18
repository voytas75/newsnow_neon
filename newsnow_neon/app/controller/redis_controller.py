"""Redis diagnostics controller.

Updates: v0.52 - 2025-11-18 - Minimal wrapper for meter updates.
"""
from __future__ import annotations
import logging
import threading
import tkinter as tk
from tkinter import messagebox
from ...cache import get_redis_client
from ...config import REDIS_URL, CACHE_KEY
from ...models import RedisStatistics
from ...app.services import collect_redis_statistics
from ...ui.windows.redis_stats_window import RedisStatsWindow


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

    def open_stats(self) -> None:
        if getattr(self.app, "_loading_redis_stats", False):
            return
        if not REDIS_URL:
            messagebox.showinfo(
                "Redis Statistics",
                "Redis caching is disabled. Set REDIS_URL to enable diagnostics.",
            )
            return
        self.app._loading_redis_stats = True
        try:
            self.app.redis_stats_btn.config(state=tk.DISABLED)
        except Exception:
            logging.getLogger(__name__).debug(
                "Unable to disable Redis stats button before loading."
            )
        threading.Thread(target=self.load_stats_worker, daemon=True).start()

    def load_stats_worker(self) -> None:
        try:
            stats = collect_redis_statistics()
        except Exception as exc:  # pragma: no cover - defensive guard
            logging.getLogger(__name__).exception("Failed to collect Redis statistics.")
            stats = RedisStatistics(
                cache_configured=bool(REDIS_URL),
                available=False,
                cache_key=CACHE_KEY,
                key_present=False,
                warnings=[f"Unable to collect Redis statistics: {exc}"],
                error=str(exc),
            )
        self.app.after(0, lambda: self.handle_stats_ready(stats))

    def handle_stats_ready(self, stats: RedisStatistics) -> None:
        self.app._loading_redis_stats = False
        button_state = tk.NORMAL if REDIS_URL else tk.DISABLED
        try:
            self.app.redis_stats_btn.config(state=button_state)
        except Exception:
            logging.getLogger(__name__).debug(
                "Unable to restore Redis stats button state."
            )

        if not stats.available:
            detail = (
                "\n".join(stats.warnings)
                if stats.warnings
                else "Redis cache unavailable."
            )
            messagebox.showwarning("Redis Statistics", detail)
            return

        if (
            getattr(self.app, "_redis_stats_window", None)
            and self.app._redis_stats_window.winfo_exists()
        ):
            self.app._redis_stats_window.update_stats(stats)
            self.app._redis_stats_window.deiconify()
            self.app._redis_stats_window.lift()
            self.app._redis_stats_window.focus_force()
            return

        try:
            self.app._redis_stats_window = RedisStatsWindow(
                self.app,
                stats,
                timezone_name=self.app._timezone_name,
                timezone_obj=self.app._timezone,
                on_close=self.app._on_redis_stats_closed,
            )
        except Exception:
            self.app._redis_stats_window = None
            logging.getLogger(__name__).exception(
                "Failed to open Redis stats window."
            )
            messagebox.showerror(
                "Redis Statistics",
                "Unable to open Redis statistics window. See logs for details.",
            )

    def on_stats_closed(self) -> None:
        self.app._redis_stats_window = None
        if not hasattr(self.app, "redis_stats_btn"):
            return
        if getattr(self.app, "_loading_redis_stats", False):
            self.app.redis_stats_btn.config(state=tk.DISABLED)
            return
        self.app.redis_stats_btn.config(state=tk.NORMAL if REDIS_URL else tk.DISABLED)
