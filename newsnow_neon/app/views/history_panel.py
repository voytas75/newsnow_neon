"""History panel builder for AINewsApp.

Updates: v0.52 - 2025-11-18 - Extracted history controls into a view module.
"""
from __future__ import annotations

import tkinter as tk
from ...config import REDIS_URL


def build_history_panel(app: tk.Tk) -> tk.Frame:
    """Create history controls (status, refresh, exit) header row."""
    history_controls = tk.Frame(app.options_container, bg="black")
    history_controls.pack(fill="x", pady=(0, 5))

    history_label = tk.Label(
        history_controls,
        text="History (last 24h):",
        bg="black",
        fg="lightgray",
        font=("Segoe UI", 10, "bold"),
    )
    history_label.pack(side="left")

    app.history_status_var = tk.StringVar(
        value="History mode off — refresh to browse cached snapshots."
    )
    history_status_label = tk.Label(
        history_controls,
        textvariable=app.history_status_var,
        bg="black",
        fg="#89CFF0",
        font=("Segoe UI", 10, "italic"),
    )
    history_status_label.pack(side="left", padx=(10, 0))

    app.exit_history_btn = tk.Button(
        history_controls,
        text="Return to Live",
        command=lambda: getattr(app, "_exit_history_mode")(),
        state=tk.DISABLED,
    )
    app.exit_history_btn.pack(side="right")

    app.history_reload_btn = tk.Button(
        history_controls,
        text="Refresh History",
        command=lambda: getattr(app, "_request_history_refresh")(),
        state=tk.NORMAL if REDIS_URL else tk.DISABLED,
    )
    app.history_reload_btn.pack(side="right", padx=(0, 10))

    return history_controls
