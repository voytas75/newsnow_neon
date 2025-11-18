from __future__ import annotations

import tkinter as tk


def build_highlight_panel(app: tk.Tk) -> tk.Frame:
    """Build the highlight keywords panel.

    Creates:
    - Label "Highlight keywords:"
    - Entry bound to app.highlight_keywords_var
    - Apply button wired to highlight_controller
    - Hint label with formatting instructions

    Returns:
        tk.Frame: The container frame for the highlight panel.
    """
    # Parent container (reuse options_container created elsewhere)
    parent = getattr(app, "options_container", None)
    if parent is None or not isinstance(parent, tk.Frame):
        parent = tk.Frame(app, name="options_container", bg="black")
        parent.pack(fill="x", padx=10, pady=(0, 10))
        setattr(app, "options_container", parent)

    highlight_frame = tk.Frame(parent, bg="black")
    highlight_frame.pack(fill="x", pady=(0, 10))

    # Label
    highlight_label = tk.Label(
        highlight_frame,
        text="Highlight keywords:",
        bg="black",
        fg="lightgray",
    )
    highlight_label.pack(side="left")

    # Entry bound to app.highlight_keywords_var
    highlight_entry = tk.Entry(
        highlight_frame,
        textvariable=getattr(app, "highlight_keywords_var"),
        width=60,
        highlightthickness=0,
    )
    highlight_entry.pack(side="left", padx=(10, 6), fill="x", expand=True)
    # Wire Return to controller method
    try:
        highlight_entry.bind(
            "<Return>",
            getattr(app, "highlight_controller").on_highlight_keywords_return,
        )
    except Exception:
        pass

    # Apply button
    apply_btn = tk.Button(
        highlight_frame,
        text="Apply",
        command=getattr(app, "highlight_controller").on_highlight_keywords_button,
    )
    apply_btn.pack(side="left")

    # Store entry reference on app for compatibility
    setattr(app, "highlight_entry", highlight_entry)

    # Hint label below the row
    hint = tk.Label(
        parent,
        text=(
            "Format: keyword:#HEX; term2:#HEX (leave blank to use defaults "
            "or NEWS_HIGHLIGHT_KEYWORDS)."
        ),
        bg="black",
        fg="#888888",
        font=("Segoe UI", 9, "italic"),
        justify="left",
        wraplength=760,
    )
    hint.pack(fill="x", padx=4, pady=(0, 5))

    return highlight_frame