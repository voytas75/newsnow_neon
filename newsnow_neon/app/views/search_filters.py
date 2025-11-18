"""Search and section filter panel.

Updates: v0.52 - 2025-11-18 - Extracted search/filter UI builder.
"""
from __future__ import annotations

import tkinter as tk


def build_search_filters(app: tk.Tk) -> tk.Frame:
    """Create search, section filter and exclusion inputs with bindings."""
    search_frame = tk.Frame(app, bg="black")

    search_label = tk.Label(search_frame, text="Search:", bg="black", fg="lightgray")
    search_label.pack(side="left")

    app.search_entry = tk.Entry(
        search_frame,
        textvariable=getattr(app, "search_var"),
        width=32,
        highlightthickness=0,
    )
    app.search_entry.pack(side="left", padx=(6, 6))
    app.search_entry.bind("<Escape>", getattr(app, "_clear_search"))

    clear_button = tk.Button(search_frame, text="Clear", command=getattr(app, "_clear_search"))
    clear_button.pack(side="left")

    filter_label = tk.Label(search_frame, text="Section:", bg="black", fg="lightgray")
    filter_label.pack(side="left", padx=(12, 4))

    app.section_filter_menu = tk.OptionMenu(
        search_frame,
        getattr(app, "section_filter_var"),
        *getattr(app, "_section_filter_options"),
    )
    app.section_filter_menu.configure(bg="#2f2f2f", fg="white", highlightthickness=0)
    app.section_filter_menu["menu"].configure(bg="#2f2f2f", fg="white")
    app.section_filter_menu.pack(side="left")

    exclude_label = tk.Label(
        search_frame,
        text="Exclude terms:",
        bg="black",
        fg="lightgray",
    )
    exclude_label.pack(side="left", padx=(12, 4))

    app.exclude_entry = tk.Entry(
        search_frame,
        textvariable=getattr(app, "exclude_terms_var"),
        width=40,
        highlightthickness=0,
    )
    app.exclude_entry.pack(side="left", padx=(6, 6))
    app.exclude_entry.bind("<Return>", getattr(app, "_apply_exclusion_terms"))
    app.exclude_entry.bind("<FocusOut>", getattr(app, "_apply_exclusion_terms"))

    apply_exclude_btn = tk.Button(search_frame, text="Apply", command=getattr(app, "_apply_exclusion_terms"))
    apply_exclude_btn.pack(side="left")

    clear_exclude_btn = tk.Button(search_frame, text="Clear", command=getattr(app, "_clear_exclusion_terms"))
    clear_exclude_btn.pack(side="left", padx=(6, 0))

    return search_frame
