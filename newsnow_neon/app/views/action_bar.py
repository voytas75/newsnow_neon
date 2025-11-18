"""Action bar builder for AINewsApp.

Updates: v0.52 - 2025-11-18 - Extracted action bar controls into a view module.
"""
from __future__ import annotations

import tkinter as tk


def build_action_bar(app: tk.Tk) -> tk.Frame:
    """Create the top action bar with options, refresh, info and exit."""
    action_bar = tk.Frame(app, bg="black")
    action_bar.pack(fill="x", padx=10, pady=(0, 10))
    app.action_bar = action_bar

    app.options_toggle_btn = tk.Button(
        action_bar,
        text="Show Options",
        command=getattr(app, "_toggle_options_panel"),
    )
    app.options_toggle_btn.pack(side="left")

    app.action_refresh_btn = tk.Button(
        action_bar,
        text="Refresh",
        command=lambda: getattr(app, "refresh_headlines")(force_refresh=True),
    )
    app.action_refresh_btn.pack(side="left", padx=(10, 0))

    right_action_cluster = tk.Frame(action_bar, bg="black")
    right_action_cluster.pack(side="right")

    app.status_summary_var = tk.StringVar(value="")
    app.status_summary_label = tk.Label(
        right_action_cluster,
        textvariable=app.status_summary_var,
        bg="black",
        fg="#89CFF0",
        font=("Segoe UI", 10, "italic"),
    )
    # initially hidden; application toggles visibility
    app.status_summary_label.pack_forget()

    app.exit_btn = tk.Button(right_action_cluster, text="Exit", command=getattr(app, "_on_close"))
    app.exit_btn.pack(side="right", padx=(10, 0))

    app.info_btn = tk.Button(right_action_cluster, text="Info", command=getattr(app, "_show_info_window"))
    app.info_btn.pack(side="right", padx=(10, 0))

    # One-click mute actions for selected headline.
    app.mute_keyword_btn = tk.Button(
        right_action_cluster,
        text="Mute Keyword",
        command=getattr(app, "_mute_selected_keyword"),
        state=tk.DISABLED,
    )
    app.mute_keyword_btn.pack(side="right", padx=(10, 0))

    app.mute_source_btn = tk.Button(
        right_action_cluster,
        text="Mute Source",
        command=getattr(app, "_mute_selected_source"),
        state=tk.DISABLED,
    )
    app.mute_source_btn.pack(side="right", padx=(10, 0))

    return action_bar
