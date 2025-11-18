"""Highlight panel builder for AINewsApp.

Updates: v0.52 - 2025-11-18 - Extracted highlight inputs and actions.
"""
from __future__ import annotations

import tkinter as tk


def build_highlight_panel(app: tk.Tk) -> tk.Frame:
    """Create the highlight keywords entry, apply button and hint."""
    highlight_frame = tk.Frame(app.options_container, bg="black")
    highlight_frame.pack(fill="x", pady=(0, 10))

    highlight_label = tk.Label(
        highlight_frame,
        text="Highlight keywords:",
        bg="black",
        fg="lightgray",
    )
    highlight_label.pack(side="left")

    app.highlight_entry = tk.Entry(
        highlight_frame,
        textvariable=getattr(app, "highlight_keywords_var"),
        width=60,
        highlightthickness=0,
    )
    app.highlight_entry.pack(side="left", padx=(10, 6), fill="x", expand=True)
    app.highlight_entry.bind("<Return>", getattr(app, "_on_highlight_keywords_return"))

    highlight_apply_btn = tk.Button(
        highlight_frame,
        text="Apply",
        command=getattr(app, "_on_highlight_keywords_button"),
    )
    highlight_apply_btn.pack(side="left")

    highlight_hint = tk.Label(
        app.options_container,
        text=(
            "Format: keyword:#HEX; term2:#HEX "
            "(leave blank to use defaults or NEWS_HIGHLIGHT_KEYWORDS)."
        ),
        bg="black",
        fg="#888888",
        font=("Segoe UI", 9, "italic"),
        justify="left",
        wraplength=760,
    )
    highlight_hint.pack(fill="x", padx=4, pady=(0, 5))

    return highlight_frame
