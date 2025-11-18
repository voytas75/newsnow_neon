"""Action bar builder for the AINewsApp main window.

Updates: v0.52 - 2025-11-18 - Introduced action bar view builder to move
widget construction out of AINewsApp; delegates commands to controllers
to preserve behavior while reducing application.py size.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Avoid circular import at runtime
    from ...application import AINewsApp


def build_action_bar(app: "AINewsApp") -> tk.Frame:
    """Create and wire the top action bar for the main window.

    The builder attaches created widgets back on the app instance to keep
    compatibility with existing code paths (status summary and mute state
    updates). Commands are delegated to controllers to preserve behavior.
    """
    action_bar = tk.Frame(app, bg="black")
    action_bar.pack(fill="x", padx=10, pady=(0, 10))
    app.action_bar = action_bar

    # Options toggle
    app.options_toggle_btn = tk.Button(
        action_bar,
        text="Show Options",
        command=app.settings_controller.toggle_options_panel,
    )
    app.options_toggle_btn.pack(side="left")

    # Manual refresh
    app.action_refresh_btn = tk.Button(
        action_bar,
        text="Refresh",
        command=lambda: app.refresh_controller.refresh_headlines(force_refresh=True),
    )
    app.action_refresh_btn.pack(side="left", padx=(10, 0))

    # Right-side cluster: status, exit, info, mute actions
    right_action_cluster = tk.Frame(action_bar, bg="black")
    right_action_cluster.pack(side="right")

    app.status_summary_var = getattr(app, "status_summary_var", tk.StringVar(value=""))
    app.status_summary_label = tk.Label(
        right_action_cluster,
        textvariable=app.status_summary_var,
        bg="black",
        fg="#89CFF0",
        font=("Segoe UI", 10, "italic"),
    )
    app.status_summary_label.pack(side="right", padx=(10, 0))
    # Hidden by default; AINewsApp/_update_status_summary toggles visibility
    app.status_summary_label.pack_forget()

    app.exit_btn = tk.Button(right_action_cluster, text="Exit", command=app._on_close)
    app.exit_btn.pack(side="right", padx=(10, 0))

    app.info_btn = tk.Button(
        right_action_cluster, text="Info", command=app._show_info_window
    )
    app.info_btn.pack(side="right", padx=(10, 0))

    # One-click mute actions for selected headline.
    app.mute_keyword_btn = tk.Button(
        right_action_cluster,
        text="Mute Keyword",
        command=app.exclusions_controller.mute_selected_keyword,
        state=tk.DISABLED,
    )
    app.mute_keyword_btn.pack(side="right", padx=(10, 0))

    app.mute_source_btn = tk.Button(
        right_action_cluster,
        text="Mute Source",
        command=app.exclusions_controller.mute_selected_source,
        state=tk.DISABLED,
    )
    app.mute_source_btn.pack(side="right", padx=(10, 0))

    return action_bar


__all__ = ["build_action_bar"]