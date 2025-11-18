"""SelectionController centralizes listbox selection, navigation, and tooltips.

Updates: v0.52 - 2025-11-18 - Introduce controller scaffold to move list view
selection and interaction logic out of AINewsApp; initial delegation keeps UI
mutations in the app to preserve behavior while refactoring incrementally.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, TYPE_CHECKING

import tkinter as tk

from ...models import Headline, HeadlineTooltipData
from ...highlight import compose_headline_tooltip

if TYPE_CHECKING:
    # Forward-declare to avoid circular imports at runtime.
    from ...application import AINewsApp


logger = logging.getLogger(__name__)


class SelectionController:
    """Encapsulates listbox selection, keyboard navigation, and tooltips.

    This scaffold delegates to the app's current methods to avoid behavior
    changes during incremental extraction; subsequent refactors can migrate
    widget mutations and tag management fully into this controller.
    """

    def __init__(self, app: "AINewsApp") -> None:
        """Bind to the Tk application orchestrator instance."""
        self.app = app

    # Public API - selection and navigation

    def clear_selection(self) -> None:
        """Clear listbox selection and hide tooltip."""
        self.app._clear_listbox_selection()
        try:
            if hasattr(self.app, "_listbox_tooltip"):
                self.app._listbox_tooltip.hide()
        except Exception:
            logger.debug("Unable to hide listbox tooltip during clear selection.")

    def select_line(self, line: int) -> None:
        """Select the given listbox line and ensure it is visible."""
        self.app._select_listbox_line(line)
        try:
            self.app.listbox.see(f"{line}.0")
        except Exception:
            logger.debug("Unable to see selected line: %s", line)

    def on_click(self, event: tk.Event) -> str:
        """Handle mouse click inside the listbox."""
        try:
            index = self.app.listbox.index(f"@{event.x},{event.y}")
        except tk.TclError:
            self.app._clear_listbox_selection()
            return "break"

        line: Optional[int] = None
        for tag in self.app.listbox.tag_names(index):
            if tag.startswith("row_"):
                candidate = self.app._row_tag_to_line.get(tag)
                if candidate is not None:
                    line = candidate
                    break

        if line is None:
            try:
                line = int(float(index.split(".")[0]))
            except (ValueError, IndexError):
                line = None

        if line is None:
            self.app._clear_listbox_selection()
            return "break"

        if line not in self.app._listbox_line_to_headline:
            for offset in (1, -1, 2, -2, 3, -3):
                probe = line + offset
                if probe in self.app._listbox_line_to_headline:
                    line = probe
                    break
            else:
                self.app._clear_listbox_selection()
                return "break"

        self.app._select_listbox_line(line)
        try:
            self.app.listbox.see(f"{line}.0")
        except Exception:
            logger.debug("Unable to see selected line in on_click")
        self.app._refresh_mute_button_state()
        return "break"

    def on_nav(self, delta: int) -> str:
        """Handle up/down keyboard navigation."""
        if not self.app._listbox_line_to_headline:
            return "break"
        sorted_lines = sorted(self.app._listbox_line_to_headline.keys())
        if not sorted_lines:
            return "break"

        if (
            self.app._selected_line is None
            or self.app._selected_line not in self.app._listbox_line_to_headline
        ):
            line = sorted_lines[0] if delta > 0 else sorted_lines[-1]
        else:
            current_index = sorted_lines.index(self.app._selected_line)
            new_index = current_index + delta
            new_index = max(0, min(len(sorted_lines) - 1, new_index))
            line = sorted_lines[new_index]

        self.app._select_listbox_line(line)
        try:
            self.app.listbox.see(f"{line}.0")
        except Exception:
            logger.debug("Unable to see selected line in on_nav")
        self.app._refresh_mute_button_state()
        return "break"

    def open_selected(self, event: tk.Event) -> None:
        """Open the currently selected headline (summary window)."""
        self.app.open_selected_headline(event)

    def resolve_selected(self) -> Optional[Headline]:
        """Resolve the Headline instance for the current selection."""
        return self.app._resolve_selected_headline()

    # Hover tooltips

    def on_motion(self, event: tk.Event) -> None:
        """Handle mouse motion for hover tooltip updates."""
        if not self.app._listbox_line_to_headline:
            try:
                if hasattr(self.app, "_listbox_tooltip"):
                    self.app._listbox_tooltip.hide()
            except Exception:
                pass
            self.app._listbox_hover_line = None
            self.app._listbox_last_tooltip_text = None
            return

        try:
            index = self.app.listbox.index(f"@{event.x},{event.y}")
        except tk.TclError:
            try:
                if hasattr(self.app, "_listbox_tooltip"):
                    self.app._listbox_tooltip.hide()
            except Exception:
                pass
            self.app._listbox_hover_line = None
            self.app._listbox_last_tooltip_text = None
            return

        line = int(float(index.split(".")[0]))
        context = self.app._listbox_line_details.get(line)
        candidate_line = line
        candidate_index = index

        if context is None:
            for offset in (-1, 1, -2, 2):
                probe = line + offset
                if probe < 1:
                    continue
                probe_context = self.app._listbox_line_details.get(probe)
                if probe_context is not None:
                    context = probe_context
                    candidate_line = probe
                    candidate_index = f"{probe}.0"
                    break

        if context is None:
            try:
                if hasattr(self.app, "_listbox_tooltip"):
                    self.app._listbox_tooltip.hide()
            except Exception:
                pass
            self.app._listbox_hover_line = None
            self.app._listbox_last_tooltip_text = None
            return

        tooltip_text = compose_headline_tooltip(
            context.headline, relative_age=context.relative_age
        )
        if (
            candidate_line != self.app._listbox_hover_line
            or tooltip_text != (self.app._listbox_last_tooltip_text or "")
        ):
            self.app._listbox_hover_line = candidate_line
            self.app._listbox_last_tooltip_text = tooltip_text
            x_root, y_root = self.tooltip_coords(candidate_index, event)
            try:
                self.app._listbox_tooltip.show(tooltip_text, x_root, y_root)
            except Exception:
                logger.debug("Unable to show tooltip")
        else:
            x_root, y_root = self.tooltip_coords(candidate_index, event)
            try:
                self.app._listbox_tooltip.move(x_root, y_root)
            except Exception:
                logger.debug("Unable to move tooltip")

    def on_leave(self, event: tk.Event) -> None:
        """Handle mouse leaving the listbox; hide current tooltip."""
        self.app._on_listbox_leave(event)

    def tooltip_coords(self, index: str, event: tk.Event) -> Tuple[int, int]:
        """Compute tooltip root coordinates for the given index and event."""
        return self.app._tooltip_coords(index, event)

    # Rendering and tag helpers (delegation for incremental extraction)

    def ensure_color_tag(self, color: str) -> str:
        """Return a tag name for the given foreground color, creating as needed."""
        return self.app.list_renderer.ensure_color_tag(color)

    def append_group_label(self, text: str) -> None:
        """Append a group label line to the listbox."""
        self.app.list_renderer.append_group_label(text)

    def append_headline_row(
        self,
        *,
        display_index: int,
        localized: Headline,
        metadata_text: str,
        relative_label: Optional[str],
        row_color: Optional[str],
        original_idx: int,
    ) -> None:
        """Append a headline row with metadata and color tags."""
        self.app.list_renderer.append_headline_row(
            display_index=display_index,
            localized=localized,
            metadata_text=metadata_text,
            relative_label=relative_label,
            row_color=row_color,
            original_idx=original_idx,
        )

    def append_message_line(self, text: str) -> None:
        """Append a message line to the listbox."""
        self.app.list_renderer.append_message_line(text)

    # Mute action integration

    def refresh_mute_buttons(self) -> None:
        """Refresh 'Mute Source' and 'Mute Keyword' button enabled states."""
        self.app._refresh_mute_button_state()

    # Convenience passthrough for listbox metadata lookups

    def line_details(self, line: int) -> Optional[HeadlineTooltipData]:
        """Return tooltip data context for a given listbox line."""
        return self.app._listbox_line_details.get(line)

    def line_metadata_text(self, line: int) -> Optional[str]:
        """Return cached metadata text for a given listbox line."""
        return self.app._listbox_line_metadata.get(line)

    def line_prefix_length(self, line: int) -> int:
        """Return prefix (title) character count for a given listbox line."""
        return int(self.app._listbox_line_prefix.get(line, 0))


__all__ = ["SelectionController"]