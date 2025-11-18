"""History panel builder for NewsNow Neon Tkinter app.

Constructs the history controls and listbox, wiring all callbacks to the
HistoryController while assigning created widgets back onto the app instance.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from ...config import REDIS_URL
from ...models import HoverTooltip

if TYPE_CHECKING:
    from ...application import AINewsApp


def build_history_panel(app: "AINewsApp") -> tk.Frame:
    """Build the history controls and listbox panel inside options_container.

    This function:
    - Creates the controls row (label, status, Return to Live, Refresh History)
    - Creates the listbox section with scrollbar and tooltip
    - Wires all commands and bindings to HistoryController methods
    - Assigns created widgets to the app instance for later use
    """
    # Controls row
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

    if not hasattr(app, "history_status_var"):
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
        command=app.history_controller.exit_history_mode,
        state=tk.DISABLED,
    )
    app.exit_history_btn.pack(side="right")

    app.history_reload_btn = tk.Button(
        history_controls,
        text="Refresh History",
        command=app.history_controller.request_history_refresh,
        state=tk.NORMAL if REDIS_URL else tk.DISABLED,
    )
    app.history_reload_btn.pack(side="right", padx=(0, 10))

    # Listbox section
    history_list_frame = tk.Frame(app.options_container, bg="black")
    history_list_frame.pack(fill="x", pady=(0, 10))

    history_scrollbar = tk.Scrollbar(history_list_frame)
    history_scrollbar.pack(side="right", fill="y")

    app.history_listbox = tk.Listbox(
        history_list_frame,
        height=6,
        font=("Segoe UI", 11),
        activestyle="none",
        bg="#101010",
        fg="white",
        selectbackground="#3A506B",
        selectforeground="white",
        yscrollcommand=history_scrollbar.set,
    )
    app.history_listbox.pack(fill="both", expand=False)
    history_scrollbar.config(command=app.history_listbox.yview)

    app.history_listbox.insert(
        tk.END,
        "History snapshots appear here when Redis history caching is enabled.",
    )
    app.history_listbox.configure(state=tk.DISABLED)

    # Bindings
    app.history_listbox.bind(
        "<<ListboxSelect>>", app.history_controller.on_history_select
    )
    app.history_listbox.bind(
        "<Double-Button-1>", app.history_controller.activate_history_selection
    )
    app.history_listbox.bind(
        "<Return>", app.history_controller.activate_history_selection
    )

    app.history_listbox_hover = HoverTooltip(app.history_listbox, wraplength=360)
    app.history_listbox.bind(
        "<Motion>", app.history_controller.on_history_motion
    )
    app.history_listbox.bind(
        "<Leave>", lambda _event: app.history_listbox_hover.hide()
    )

    return history_controls