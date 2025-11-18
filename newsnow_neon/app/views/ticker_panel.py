from __future__ import annotations

import tkinter as tk
from typing import Tuple

from ...ui import NewsTicker


def build_ticker_panel(app: tk.Tk) -> Tuple[NewsTicker, NewsTicker]:
    """Create primary and full tickers and attach them to the app.

    Returns:
        Tuple[NewsTicker, NewsTicker]: (ticker, full_ticker) created widgets.
    """
    ticker = NewsTicker(app, name="neon1")
    ticker.pack(fill="x", padx=10, pady=(10, 5))

    full_ticker = NewsTicker(
        app,
        speed=1,
        max_title_length=None,
        font_spec=("Consolas", 14, "bold"),
        item_spacing=120,
        name="neon2",
    )
    full_ticker.pack(fill="x", padx=10, pady=(0, 10))

    # Attach to app for downstream usage
    setattr(app, "ticker", ticker)
    setattr(app, "full_ticker", full_ticker)

    return ticker, full_ticker