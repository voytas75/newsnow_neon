"""Search and filter panel builder for NewsNow Neon Tkinter app."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...application import AINewsApp


def build_search_filters(app: "AINewsApp") -> tk.Frame:
    """Construct the search, section filter, and exclusion controls row.

    Wires callbacks to existing application methods to preserve behavior and
    assigns created widgets back onto the app where other methods expect them.
    """
    frame = tk.Frame(app, bg="black")

    # Search
    search_label = tk.Label(frame, text="Search:", bg="black", fg="lightgray")
    search_label.pack(side="left")

    app.search_entry = tk.Entry(
        frame,
        textvariable=app.search_var,
        width=32,
        highlightthickness=0,
    )
    app.search_entry.pack(side="left", padx=(6, 6))
    app.search_entry.bind("<Escape>", app._clear_search)

    clear_button = tk.Button(frame, text="Clear", command=app._clear_search)
    clear_button.pack(side="left")

    # Section filter
    filter_label = tk.Label(frame, text="Section:", bg="black", fg="lightgray")
    filter_label.pack(side="left", padx=(12, 4))

    app.section_filter_menu = tk.OptionMenu(
        frame,
        app.section_filter_var,
        *app._section_filter_options,
    )
    app.section_filter_menu.configure(bg="#2f2f2f", fg="white", highlightthickness=0)
    app.section_filter_menu["menu"].configure(bg="#2f2f2f", fg="white")
    app.section_filter_menu.pack(side="left")

    # Exclusion terms
    exclude_label = tk.Label(
        frame,
        text="Exclude terms:",
        bg="black",
        fg="lightgray",
    )
    exclude_label.pack(side="left", padx=(12, 4))

    app.exclude_entry = tk.Entry(
        frame,
        textvariable=app.exclude_terms_var,
        width=40,
        highlightthickness=0,
    )
    app.exclude_entry.pack(side="left", padx=(6, 6))
    app.exclude_entry.bind("<Return>", app._apply_exclusion_terms)
    app.exclude_entry.bind("<FocusOut>", app._apply_exclusion_terms)

    apply_exclude_btn = tk.Button(
        frame,
        text="Apply",
        command=app._apply_exclusion_terms,
    )
    apply_exclude_btn.pack(side="left")

    clear_exclude_btn = tk.Button(
        frame,
        text="Clear",
        command=app._clear_exclusion_terms,
    )
    clear_exclude_btn.pack(side="left", padx=(6, 0))

    return frame