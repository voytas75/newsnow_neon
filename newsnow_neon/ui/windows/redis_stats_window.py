"""Redis stats window extracted from ui.py.

Updates: v0.52 - 2025-11-18 - Extracted RedisStatsWindow into ui/windows.
"""
from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime, timezone, tzinfo
from typing import Dict, List, Optional

from ...models import RedisStatistics

logger = logging.getLogger(__name__)


class RedisStatsWindow(tk.Toplevel):
    """Display current Redis cache metrics and payload insight."""

    def __init__(
        self,
        master: tk.Misc,
        stats: RedisStatistics,
        timezone_name: str,
        timezone_obj: tzinfo,
        on_close: Optional[callable],
    ) -> None:
        super().__init__(master)
        self._on_close = on_close
        self._timezone_name = timezone_name
        self._timezone = timezone_obj
        self._closed = False

        self.title("Redis Cache Statistics")
        self.configure(bg="black")
        self.resizable(False, False)
        self.transient(master)
        self.geometry("560x560")
        self.protocol("WM_DELETE_WINDOW", self._handle_close)
        self.bind("<Escape>", lambda _event: self._handle_close())

        header = tk.Label(
            self,
            text="Redis diagnostics",
            font=("Segoe UI", 14, "bold"),
            bg="black",
            fg="white",
        )
        header.pack(pady=(16, 6))

        subtitle = tk.Label(
            self,
            text=f"Timezone: {timezone_name}",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10),
        )
        subtitle.pack(pady=(0, 12))

        info_frame = tk.Frame(self, bg="black")
        info_frame.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        self._field_order = [
            "Cache key",
            "Key present",
            "Headlines",
            "Sections",
            "Sources",
            "Summaries",
            "Ticker text",
            "TTL",
            "Payload size",
            "Latest headline",
            "Latest headline timestamp",
            "Historical snapshots",
            "Latest snapshot key",
            "Redis version",
            "Connected clients",
            "Database keys",
            "Used memory",
        ]
        self._field_vars: Dict[str, tk.StringVar] = {}
        for label_text in self._field_order:
            var = tk.StringVar(value="…")
            self._add_row(info_frame, label_text, var)
            self._field_vars[label_text] = var

        warnings_label = tk.Label(
            info_frame,
            text="Warnings",
            bg="black",
            fg="#FFA94D",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        warnings_label.pack(fill="x", pady=(12, 2))

        self._warnings_var = tk.StringVar(value="No warnings.")
        warnings_value = tk.Label(
            info_frame,
            textvariable=self._warnings_var,
            bg="black",
            fg="#FFCD94",
            justify="left",
            wraplength=500,
            anchor="w",
        )
        warnings_value.pack(fill="x")

        button_row = tk.Frame(self, bg="black")
        button_row.pack(fill="x", padx=18, pady=(0, 18))
        close_btn = tk.Button(button_row, text="Close", command=self._handle_close)
        close_btn.pack(side="right")

        self.update_stats(stats)

    def _add_row(
        self, container: tk.Frame, label_text: str, value_var: tk.StringVar
    ) -> None:
        row = tk.Frame(container, bg="black")
        row.pack(fill="x", pady=2)
        label = tk.Label(
            row,
            text=f"{label_text}:",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10, "bold"),
            width=24,
            anchor="w",
        )
        label.pack(side="left")
        value_label = tk.Label(
            row,
            textvariable=value_var,
            bg="black",
            fg="white",
            justify="left",
            wraplength=420,
            anchor="w",
        )
        value_label.pack(fill="x", expand=True, side="left")

    def update_stats(self, stats: RedisStatistics) -> None:
        values = self._format_values(stats)
        for label_text, value in values.items():
            if label_text in self._field_vars:
                self._field_vars[label_text].set(value)
        warnings_text = "No warnings."
        if stats.warnings:
            warnings_text = "\n".join(stats.warnings)
        self._warnings_var.set(warnings_text)

    def _format_values(self, stats: RedisStatistics) -> Dict[str, str]:
        latest_timestamp = self._format_latest_timestamp(stats)
        return {
            "Cache key": stats.cache_key,
            "Key present": self._format_bool(stats.key_present),
            "Headlines": f"{stats.headline_count}",
            "Sections": self._format_sequence(stats.sections),
            "Sources": self._format_sequence(stats.sources),
            "Summaries": f"{stats.summary_count}",
            "Ticker text": "Present" if stats.ticker_present else "Absent",
            "TTL": self._format_ttl(stats),
            "Payload size": self._format_bytes(stats.payload_bytes),
            "Latest headline": self._format_latest_headline(stats),
            "Latest headline timestamp": latest_timestamp,
            "Historical snapshots": str(stats.historical_snapshot_count),
            "Latest snapshot key": stats.latest_snapshot_key or "n/a",
            "Redis version": stats.redis_version or "n/a",
            "Connected clients": (
                str(stats.connected_clients)
                if stats.connected_clients is not None
                else "n/a"
            ),
            "Database keys": str(stats.dbsize) if stats.dbsize is not None else "n/a",
            "Used memory": stats.used_memory_human or "n/a",
        }

    def _format_ttl(self, stats: RedisStatistics) -> str:
        if not stats.key_present:
            return "Key missing"
        if stats.ttl_seconds is None:
            return "No expiration"
        if stats.ttl_seconds < 0:
            return "Expired"
        return f"{stats.ttl_seconds}s ({self._humanise_seconds(stats.ttl_seconds)})"

    @staticmethod
    def _format_sequence(items: List[str]) -> str:
        if not items:
            return "n/a"
        if len(items) <= 6:
            return ", ".join(items)
        preview = ", ".join(items[:6])
        remainder = len(items) - 6
        return f"{preview}, +{remainder} more"

    @staticmethod
    def _format_bool(value: bool) -> str:
        return "Yes" if value else "No"

    @staticmethod
    def _humanise_seconds(seconds: int) -> str:
        if seconds <= 0:
            return "0s"
        remainder = seconds
        parts: List[str] = []
        days, remainder = divmod(remainder, 86_400)
        if days:
            parts.append(f"{days}d")
        hours, remainder = divmod(remainder, 3_600)
        if hours:
            parts.append(f"{hours}h")
        minutes, remainder = divmod(remainder, 60)
        if minutes:
            parts.append(f"{minutes}m")
        if remainder or not parts:
            parts.append(f"{remainder}s")
        return " ".join(parts)

    @staticmethod
    def _format_bytes(value: Optional[int]) -> str:
        if value is None or value < 0:
            return "n/a"
        units = ["B", "KiB", "MiB", "GiB", "TiB"]
        size = float(value)
        for index, unit in enumerate(units):
            if size < 1024.0 or index == len(units) - 1:
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TiB"

    def _format_latest_headline(self, stats: RedisStatistics) -> str:
        if not stats.latest_headline_title:
            return "n/a"
        title = stats.latest_headline_title.strip()
        if len(title) > 90:
            title = title[:87] + "…"
        if stats.latest_headline_source:
            return f"{title} ({stats.latest_headline_source})"
        return title

    def _format_latest_timestamp(self, stats: RedisStatistics) -> str:
        timestamp = stats.latest_headline_time
        if timestamp is None:
            return "n/a"
        local_dt = timestamp.astimezone(self._timezone)
        age_seconds = max(
            0, int((datetime.now(timezone.utc) - timestamp).total_seconds())
        )
        age_label = self._humanise_seconds(age_seconds)
        formatted = local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        return f"{formatted} ({age_label} ago)"

    def _handle_close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._on_close:
            try:
                self._on_close()
            except Exception:  # pragma: no cover - safeguard
                logger.exception("Error running Redis stats close callback.")
        self.destroy()


__all__ = ["RedisStatsWindow"]