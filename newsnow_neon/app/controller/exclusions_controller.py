"""ExclusionsController centralizes exclusions parsing and mute actions.

Updates: v0.52 - 2025-11-18 - Introduce controller scaffold that delegates to
existing AINewsApp methods to preserve behavior while refactoring; subsequent
iterations can migrate parsing and rendering responsibilities fully here.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Set, Tuple, TYPE_CHECKING

import tkinter as tk

from ...models import Headline

if TYPE_CHECKING:
    # Forward-declare to avoid circular import at runtime.
    from ...application import AINewsApp


logger = logging.getLogger(__name__)


class ExclusionsController:
    """Encapsulates exclusions workflow and one-click mute actions.

    This controller is initially a thin delegation layer to the current
    AINewsApp methods. It enables wiring UI commands and event bindings
    away from the monolith; future changes can move core logic here.
    """

    def __init__(self, app: "AINewsApp") -> None:
        """Bind to the Tk application orchestrator instance."""
        self.app = app

    # Public API — event/binding handlers

    def apply_exclusion_terms(self, event: Optional[tk.Event] = None) -> Optional[str]:
        """Apply exclusions from the current entry var; keep Return 'break' behavior."""
        return self.app._apply_exclusion_terms(event)

    def clear_exclusion_terms(self) -> None:
        """Clear all configured exclusion terms."""
        self.app._clear_exclusion_terms()

    # One-click mute actions

    def mute_selected_source(self) -> None:
        """Mute the source (final domain or derived label) of selected headline."""
        self.app._mute_selected_source()

    def mute_selected_keyword(self) -> None:
        """Mute a keyword heuristically extracted from selected headline title."""
        self.app._mute_selected_keyword()

    # Programmatic API — additive term update

    def add_exclusion_term(self, term: str, *, show_feedback: bool = True) -> bool:
        """Append a term to exclusions asynchronously and re-render on completion."""
        return self.app._add_exclusion_term(term, show_feedback=show_feedback)

    # Utilities — retained delegation for incremental extraction

    def resolve_selected_headline(self) -> Optional[Headline]:
        """Resolve the Headline object for the current selection."""
        return self.app._resolve_selected_headline()

    def normalise_exclusion_terms(self, source: Any) -> Tuple[list[str], Set[str]]:
        """Normalize free-form exclusions into canonical list and lookup set."""
        return self.app._normalise_exclusion_terms(source)

    def split_exclusion_string(self, text: str) -> list[str]:
        """Split a free-form exclusion string into normalized terms."""
        return self.app._split_exclusion_string(text)

    def filter_headlines(self, headlines: list[Headline]) -> list[Headline]:
        """Filter headlines based on exclusion terms; preserves ordering."""
        return self.app._filter_headlines(headlines)

    def refresh_mute_buttons(self) -> None:
        """Enable/disable mute buttons according to current selection state."""
        self.app._refresh_mute_button_state()


__all__ = ["ExclusionsController"]