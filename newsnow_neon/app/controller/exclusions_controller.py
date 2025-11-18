"""Exclusions controller.

Updates: v0.52 - 2025-11-18 - Minimal wrapper for term addition.
"""
from __future__ import annotations


class ExclusionsController:
    """Delegates exclusions term management to the application."""

    def __init__(self, app) -> None:
        self.app = app

    def add_term(self, term: str, *, show_feedback: bool = True) -> bool:
        return self.app._add_exclusion_term(term, show_feedback=show_feedback)
