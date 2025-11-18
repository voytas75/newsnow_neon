"""HighlightController manages highlight keywords and heatmap window state.

Updates: v0.52 - 2025-11-18 - Introduce controller scaffold delegating to
AINewsApp methods to preserve UI behavior while refactoring; subsequent
iterations can migrate parsing, persistence, and view refresh fully here.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Forward-declare to avoid circular import at runtime.
    from ...application import AINewsApp


logger = logging.getLogger(__name__)


class HighlightController:
    """Encapsulates highlight keywords workflow and heatmap UI state."""

    def __init__(self, app: "AINewsApp") -> None:
        """Bind to the Tk application orchestrator instance."""
        self.app = app

    # Public API — keyword entry interactions

    def apply_highlight_keywords_from_var(self, *, show_feedback: bool) -> None:
        """Parse, apply, persist, and refresh highlight keywords from entry var."""
        self.app.apply_highlight_keywords_from_var(show_feedback=show_feedback)

    def on_highlight_keywords_return(self, *_args: object) -> str:
        """Handle Return key in the highlight entry; keep 'break' behavior."""
        return self.app._on_highlight_keywords_return()

    def on_highlight_keywords_button(self) -> None:
        """Handle Apply button in the highlight panel."""
        self.app._on_highlight_keywords_button()

    # Heatmap window management

    def update_heatmap_button_state(self) -> None:
        """Enable/disable heatmap button and close window if pattern cleared."""
        self.app._update_heatmap_button_state()

    def open_heatmap(self) -> None:
        """Open or refresh the keyword heatmap window."""
        self.app.open_heatmap()

    def on_heatmap_closed(self) -> None:
        """Handle closing of the heatmap window."""
        self.app._on_heatmap_closed()


__all__ = ["HighlightController"]