"""Selection and list interaction controller.

Updates: v0.52 - 2025-11-18 - Minimal event handler delegation.
"""
from __future__ import annotations
import tkinter as tk


class SelectionController:
    """Wires listbox events to application handlers."""

    def __init__(self, app) -> None:
        self.app = app

    def on_click(self, event: tk.Event) -> str:
        return self.app._on_listbox_click(event)

    def on_nav(self, delta: int) -> str:
        return self.app._on_listbox_nav(delta)

    def on_motion(self, event: tk.Event) -> None:
        self.app._on_listbox_motion(event)

    def on_leave(self, event: tk.Event) -> None:
        self.app._on_listbox_leave(event)

    def open_selected(self, event: tk.Event) -> None:
        self.app.open_selected_headline(event)
