from __future__ import annotations

import tkinter as tk
from typing import Tuple


def build_logs_panel(app: tk.Tk) -> Tuple[tk.Frame, tk.Text]:
    """Create the logs panel (frame, scrollbar, text) and attach to app.

    The frame is not packed initially; visibility is controlled by the app's
    toggle logic. Scrollbar is wired to the text widget for vertical scrolling.

    Returns:
        Tuple[tk.Frame, tk.Text]: (log_frame, log_text) created widgets.
    """
    log_frame = tk.Frame(app, bg="black")

    log_scroll = tk.Scrollbar(log_frame)
    log_scroll.pack(side="right", fill="y")

    log_text = tk.Text(
        log_frame,
        wrap="word",
        bg="#101010",
        fg="lightgray",
        height=10,
        state="disabled",
        yscrollcommand=log_scroll.set,
        font=("Consolas", 11),
    )
    log_text.pack(fill="both", expand=True)
    log_scroll.config(command=log_text.yview)

    # Attach to app for downstream use
    setattr(app, "log_visible", False)
    setattr(app, "log_frame", log_frame)
    setattr(app, "log_text", log_text)

    return log_frame, log_text