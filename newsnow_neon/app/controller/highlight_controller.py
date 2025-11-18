"""Highlight keywords controller.

Updates: v0.52 - 2025-11-18 - Minimal wrapper for keyword application.
"""
from __future__ import annotations


class HighlightController:
    """Delegates highlight keyword updates to the application."""

    def __init__(self, app) -> None:
        self.app = app

    def apply_keywords_from_var(self, *, show_feedback: bool) -> None:
        self.app.apply_highlight_keywords_from_var(show_feedback=show_feedback)
