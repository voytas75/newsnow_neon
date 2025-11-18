from __future__ import annotations

import tkinter as tk
from tkinter import font
from typing import Tuple, Dict

from ...models import HoverTooltip


def build_list_view(app: tk.Tk) -> Tuple[tk.Frame, tk.Text]:
    """Build the main list view (frame, scrollbar, listbox) and attach to app.

    Creates fonts, configures text tags, sets default colors, wires scrollbar,
    and attaches helper attributes on the app instance for downstream logic.

    Returns:
        Tuple[tk.Frame, tk.Text]: (list_frame, listbox) created widgets.
    """
    list_frame = tk.Frame(app, name="list", bg="black")
    list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")

    default_font = font.nametofont("TkDefaultFont")
    base_family = default_font.actual("family") or "Segoe UI"
    base_size = max(int(default_font.actual("size")), 12)
    base_weight = default_font.actual("weight") or "normal"

    title_font = font.Font(family=base_family, size=base_size, weight=base_weight)
    metadata_font = font.Font(
        family=base_family, size=max(base_size - 2, 8), weight=base_weight, slant="italic"
    )
    group_font = font.Font(family=base_family, size=base_size, weight="bold")

    listbox_default_fg = "#FFFFFF"
    metadata_fg = "#B0B0B0"

    listbox = tk.Text(
        list_frame,
        wrap="none",
        bg="#101010",
        fg=listbox_default_fg,
        insertbackground="white",
        height=0,
        state="disabled",
        relief="flat",
    )
    listbox.pack(fill="both", expand=True)
    listbox.configure(yscrollcommand=scrollbar.set, cursor="arrow")
    scrollbar.config(command=listbox.yview)

    listbox.tag_configure("group", font=group_font, foreground="#89CFF0")
    listbox.tag_configure("title", font=title_font, foreground=listbox_default_fg)
    listbox.tag_configure("metadata", font=metadata_font, foreground=metadata_fg)
    listbox.tag_configure("message", font=title_font, foreground=listbox_default_fg)
    listbox.tag_configure("selected", background="#264653")
    listbox.tag_raise("selected")

    # Attach attributes to app for downstream logic
    setattr(app, "_listbox_title_font", title_font)
    setattr(app, "_listbox_metadata_font", metadata_font)
    setattr(app, "_listbox_group_font", group_font)
    setattr(app, "listbox_default_fg", listbox_default_fg)
    setattr(app, "_listbox_metadata_fg", metadata_fg)
    setattr(app, "listbox", listbox)
    setattr(app, "_listbox_color_tags", {})  # type: ignore[assignment]
    setattr(app, "_listbox_tooltip", HoverTooltip(listbox, wraplength=520))

    return list_frame, listbox