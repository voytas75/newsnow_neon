"""Logs panel builder.

Updates: v0.52 - 2025-11-18 - Extracted logs frame and text widget.
"""
from __future__ import annotations

import tkinter as tk
from typing import Tuple


def build_logs_panel(app) -> Tuple[tk.Frame, tk.Text]:
    """Create logs frame and text widget with scrollbar."""
    log_frame = tk.Frame(app, bg="black")
    log_scroll = tk.Scrollbar(log_frame)
    log_scroll.pack(side="right", fill="y")
    log_text = tk.Text(
        log_frame,
        wrap="word",
        bg="#101010",
        fg="lightgray",
        height=10,
        state="disabled",
        yscrollcommand=log_scroll.set,
        font=("Consolas", 11),
    )
    log_text.pack(fill="both", expand=True)
    log_scroll.config(command=log_text.yview)
    return log_frame, log_text
