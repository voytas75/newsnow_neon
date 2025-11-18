"""Selection and list interaction controller.

Updates:
- v0.52 - 2025-11-18 - Minimal event handler delegation.
- v0.52.2 - 2025-11-18 - Moved click/nav/motion/leave logic from application.py.
"""
from __future__ import annotations

import tkinter as tk
from typing import Optional, Tuple

from ...highlight import compose_headline_tooltip


class SelectionController:
    """Handles selection, navigation, hover tooltips for the list view."""

    def __init__(self, app) -> None:
        self.app = app

    def on_click(self, event: tk.Event) -> str:
        """Select a row when the user clicks inside the text list."""
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
        self.app.listbox.see(f"{line}.0")
        self.app._refresh_mute_button_state()
        return "break"

    def on_nav(self, delta: int) -> str:
        """Keyboard navigation (Up/Down) across rendered headline rows."""
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
        self.app.listbox.see(f"{line}.0")
        self.app._refresh_mute_button_state()
        return "break"

    def on_motion(self, event: tk.Event) -> None:
        """Update hover tooltip as the mouse moves across rows."""
        if not self.app._listbox_line_to_headline:
            self.app._listbox_tooltip.hide()
            self.app._listbox_hover_line = None
            self.app._listbox_last_tooltip_text = None
            return

        try:
            index = self.app.listbox.index(f"@{event.x},{event.y}")
        except tk.TclError:
            self.app._listbox_tooltip.hide()
            self.app._listbox_hover_line = None
            self.app._listbox_last_tooltip_text = None
            return

        try:
            line = int(float(index.split(".")[0]))
        except (ValueError, IndexError):
            self.app._listbox_tooltip.hide()
            self.app._listbox_hover_line = None
            self.app._listbox_last_tooltip_text = None
            return

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
            self.app._listbox_tooltip.hide()
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
            x_root, y_root = self._tooltip_coords(candidate_index, event)
            self.app._listbox_tooltip.show(tooltip_text, x_root, y_root)
        else:
            x_root, y_root = self._tooltip_coords(candidate_index, event)
            self.app._listbox_tooltip.move(x_root, y_root)

    def on_leave(self, _event: tk.Event) -> None:
        """Hide tooltip when cursor leaves the listbox region."""
        self.app._listbox_hover_line = None
        self.app._listbox_last_tooltip_text = None
        self.app._listbox_tooltip.hide()

    def open_selected(self, event: tk.Event) -> None:
        """Open summary for the selected headline."""
        self.app.open_selected_headline(event)

    def _tooltip_coords(self, index: str, event: tk.Event) -> Tuple[int, int]:
        """Find absolute coordinates for placing the hover tooltip."""
        try:
            bbox = self.app.listbox.bbox(index)
        except tk.TclError:
            bbox = None

        if not bbox:
            return event.x_root, event.y_root

        x_pix, y_pix, width, height = bbox
        width = max(width, 1)
        height = max(height, 1)
        widget_root_x = self.app.listbox.winfo_rootx()
        widget_root_y = self.app.listbox.winfo_rooty()
        x_root = widget_root_x + x_pix + width + 12
        y_root = widget_root_y + y_pix + height // 2
        return x_root, y_root
