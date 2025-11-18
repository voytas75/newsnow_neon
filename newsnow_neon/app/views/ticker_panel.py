"""Ticker panel builder.

Updates: v0.52 - 2025-11-18 - Extracted ticker widgets construction.
"""
from __future__ import annotations

from typing import Tuple
from tkinter import Frame
from ...ui.widgets.news_ticker import NewsTicker


def build_ticker_panel(app) -> Tuple[NewsTicker, NewsTicker]:
    """Create primary and full tickers and attach to the application."""
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
    return ticker, full_ticker
