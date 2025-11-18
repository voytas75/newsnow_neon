from __future__ import annotations

import tkinter as tk
from typing import Optional


def build_controls_panel(app: tk.Tk) -> tk.Frame:
    """Build controls panel with refresh and diagnostics actions.

    Creates the top controls row inside the options container:
    - Refresh Headlines
    - Clear Cache
    - Redis Stats
    - Keyword Heatmap
    - Show/Hide Logs toggle
    - Redis meter label

    The builder sets created widgets back onto the app for controller access.
    """
    parent: Optional[tk.Frame] = getattr(app, "options_container", None)
    if parent is None or not isinstance(parent, tk.Frame):
        parent = tk.Frame(app, name="options_container", bg="black")
        parent.pack(fill="x", padx=10, pady=(0, 10))
        setattr(app, "options_container", parent)

    controls = tk.Frame(parent, bg="black")
    controls.pack(fill="x", pady=(0, 10))

    refresh_btn = tk.Button(
        controls,
        text="Refresh Headlines",
        command=lambda: getattr(app, "refresh_headlines")(force_refresh=True),
    )
    refresh_btn.pack(side="left")

    clear_cache_btn = tk.Button(
        controls,
        text="Clear Cache",
        command=getattr(app, "redis_controller").clear_cache,
    )
    clear_cache_btn.pack(side="left", padx=10)
    setattr(app, "clear_cache_btn", clear_cache_btn)

    redis_stats_btn = tk.Button(
        controls,
        text="Redis Stats",
        command=getattr(app, "redis_controller").open_redis_stats,
        state=tk.DISABLED,
    )
    redis_stats_btn.pack(side="left", padx=10)
    setattr(app, "redis_stats_btn", redis_stats_btn)

    heatmap_btn = tk.Button(
        controls,
        text="Keyword Heatmap",
        command=getattr(app, "highlight_controller").open_heatmap,
        state=tk.DISABLED,
    )
    heatmap_btn.pack(side="left", padx=10)
    setattr(app, "heatmap_btn", heatmap_btn)
    try:
        getattr(app, "highlight_controller").update_heatmap_button_state()
    except Exception:
        pass

    toggle_logs_btn = tk.Button(
        controls,
        text="Show Logs",
        command=getattr(app, "_toggle_logs"),
    )
    toggle_logs_btn.pack(side="left", padx=10)
    setattr(app, "toggle_logs_btn", toggle_logs_btn)

    redis_meter_var = tk.StringVar(value="Redis: checking…")
    redis_meter_label = tk.Label(
        controls,
        textvariable=redis_meter_var,
        bg="black",
        fg="#FFB347",
        anchor="w",
    )
    redis_meter_label.pack(side="left", padx=10)
    setattr(app, "redis_meter_var", redis_meter_var)
    setattr(app, "redis_meter_label", redis_meter_label)

    # Trigger an initial meter update if controller is available
    try:
        getattr(app, "redis_controller").update_redis_meter()
    except Exception:
        pass

    return controls