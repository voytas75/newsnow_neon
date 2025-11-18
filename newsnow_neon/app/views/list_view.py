"""Main list view builder.

Updates: v0.52 - 2025-11-18 - Extracted listbox widgets and fonts/tags.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font
from typing import Tuple
from ...models import HoverTooltip  # type: ignore


def build_list_view(app) -> Tuple[tk.Frame, tk.Text]:
    """Create list frame with scrollbars, fonts, tags and text widget."""
    list_frame = tk.Frame(app, name="list", bg="black")
    list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")

    default_font = font.nametofont("TkDefaultFont")
    base_family = default_font.actual("family") or "Segoe UI"
    base_size = max(int(default_font.actual("size")), 12)
    base_weight = default_font.actual("weight") or "normal"
    app._listbox_title_font = font.Font(
        family=base_family,
        size=base_size,
        weight=base_weight,
    )
    app._listbox_metadata_font = font.Font(
        family=base_family,
        size=max(base_size - 2, 8),
        weight=base_weight,
        slant="italic",
    )
    app._listbox_group_font = font.Font(
        family=base_family,
        size=base_size,
        weight="bold",
    )
    app.listbox_default_fg = "#FFFFFF"
    app._listbox_metadata_fg = "#B0B0B0"

    listbox = tk.Text(
        list_frame,
        wrap="none",
        bg="#101010",
        fg=app.listbox_default_fg,
        insertbackground="white",
        height=0,
        state="disabled",
        relief="flat",
    )
    listbox.pack(fill="both", expand=True)
    listbox.configure(yscrollcommand=scrollbar.set, cursor="arrow")
    scrollbar.config(command=listbox.yview)
    listbox.tag_configure("group", font=app._listbox_group_font, foreground="#89CFF0")
    listbox.tag_configure("title", font=app._listbox_title_font, foreground=app.listbox_default_fg)
    listbox.tag_configure("metadata", font=app._listbox_metadata_font, foreground=app._listbox_metadata_fg)
    listbox.tag_configure("message", font=app._listbox_title_font, foreground=app.listbox_default_fg)
    listbox.tag_configure("selected", background="#264653")
    listbox.tag_raise("selected")

    app._listbox_color_tags = {}
    app._listbox_tooltip = HoverTooltip(listbox, wraplength=520)

    return list_frame, listbox
