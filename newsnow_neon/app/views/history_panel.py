"""History panel builder for AINewsApp.

Updates: v0.52 - 2025-11-18 - Extracted history controls into a view module.
"""
from __future__ import annotations

import tkinter as tk
from ...config import REDIS_URL
from ...models import HoverTooltip


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

    # History listbox + scrollbar
    history_list_frame = tk.Frame(app.options_container, bg="black")
    history_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    history_scroll = tk.Scrollbar(history_list_frame)
    history_scroll.pack(side="right", fill="y")

    app.history_listbox = tk.Listbox(
        history_list_frame,
        activestyle="none",
        bg="black",
        fg="white",
        selectbackground="#333333",
        selectforeground="white",
        highlightthickness=0,
        borderwidth=1,
        yscrollcommand=history_scroll.set,
    )
    app.history_listbox.pack(side="left", fill="both", expand=True)
    history_scroll.config(command=app.history_listbox.yview)

    # Tooltip for history listbox hover previews
    app.history_listbox_hover = HoverTooltip(app, background="#1e1e1e", foreground="white")

    # Event bindings for selection/activation and hover preview
    app.history_listbox.bind("<<ListboxSelect>>", getattr(app, "_on_history_select"))
    app.history_listbox.bind(
        "<Return>", lambda e: getattr(app, "_activate_history_selection")(e)
    )
    app.history_listbox.bind(
        "<Double-Button-1>", lambda e: getattr(app, "_activate_history_selection")(e)
    )
    app.history_listbox.bind("<Motion>", getattr(app, "_on_history_motion"))
    app.history_listbox.bind("<Leave>", lambda _e: app.history_listbox_hover.hide())

    # Initial placeholder and disabled state
    app.history_listbox.configure(state=tk.NORMAL)
    app.history_listbox.insert(tk.END, "History snapshots appear here when loaded.")
    app.history_listbox.configure(state=tk.DISABLED)

    return history_controls
