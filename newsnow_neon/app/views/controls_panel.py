"""Controls panel builder for AINewsApp.

Updates: v0.52 - 2025-11-18 - Extracted common control buttons and meters.
"""
from __future__ import annotations

import tkinter as tk
from ...config import REDIS_URL
from ...highlight import has_highlight_pattern


def build_controls_panel(app: tk.Tk) -> tk.Frame:
    """Create controls row: refresh, clear cache, redis stats, heatmap, logs, meter."""
    controls = tk.Frame(app.options_container, bg="black")
    controls.pack(fill="x", pady=(0, 10))

    refresh_btn = tk.Button(
        controls,
        text="Refresh Headlines",
        command=lambda: getattr(app, "refresh_headlines")(force_refresh=True),
    )
    refresh_btn.pack(side="left")

    app.clear_cache_btn = tk.Button(controls, text="Clear Cache", command=getattr(app, "clear_cache"))
    app.clear_cache_btn.pack(side="left", padx=10)

    app.redis_stats_btn = tk.Button(
        controls,
        text="Redis Stats",
        command=getattr(app, "_open_redis_stats"),
        state=tk.NORMAL if REDIS_URL else tk.DISABLED,
    )
    app.redis_stats_btn.pack(side="left", padx=10)

    heatmap_state = tk.NORMAL if has_highlight_pattern() else tk.DISABLED
    app.heatmap_btn = tk.Button(
        controls,
        text="Keyword Heatmap",
        command=getattr(app, "open_heatmap"),
        state=heatmap_state,
    )
    app.heatmap_btn.pack(side="left", padx=10)

    app.toggle_logs_btn = tk.Button(controls, text="Show Logs", command=getattr(app, "_toggle_logs"))
    app.toggle_logs_btn.pack(side="left", padx=10)

    app.redis_meter_var = tk.StringVar(value="Redis: checking…")
    app.redis_meter_label = tk.Label(
        controls,
        textvariable=app.redis_meter_var,
        bg="black",
        fg="#FFB347",
        anchor="w",
    )
    app.redis_meter_label.pack(side="left", padx=10)

    return controls
