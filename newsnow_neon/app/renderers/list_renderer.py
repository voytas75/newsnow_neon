"""ListRenderer centralizes listbox row rendering and tag management.

Updates: v0.52 - 2025-11-18 - Introduced renderer to extract listbox row
logic and color tag management from AINewsApp, enabling controllers and
view builders to delegate list content mutations cleanly.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

import tkinter as tk

from ...models import Headline, HeadlineTooltipData

if TYPE_CHECKING:
    # Forward declaration to avoid runtime circular import
    from ...application import AINewsApp


logger = logging.getLogger(__name__)


class ListRenderer:
    """Encapsulate listbox row rendering and color tag management."""

    def __init__(self, app: "AINewsApp") -> None:
        """Bind the renderer to the Tk app orchestrator instance."""
        self.app = app

    def ensure_line_break(self) -> None:
        """Insert a trailing newline in the listbox when needed."""
        try:
            last_char = self.app.listbox.get("end-1c")
        except tk.TclError:
            return
        if not last_char or last_char == "\n":
            return
        self.app.listbox.insert("end", "\n")

    def ensure_color_tag(self, color: str) -> str:
        """Return tag name for given foreground color, creating if missing."""
        tag = self.app._listbox_color_tags.get(color)
        if tag is not None:
            return tag
        tag = f"color_{len(self.app._listbox_color_tags)}"
        try:
            self.app.listbox.tag_configure(tag, foreground=color)
        except Exception:
            logger.debug("Unable to configure color tag: %s", color)
        self.app._listbox_color_tags[color] = tag
        return tag

    def append_group_label(self, text: str) -> None:
        """Append a group label line (e.g., '-- Recent --') to the listbox."""
        self.app.listbox.configure(state="normal")
        self.ensure_line_break()
        try:
            self.app.listbox.insert("end", text, ("group",))
            self.app.listbox.insert("end", "\n")
        finally:
            self.app.listbox.configure(state="disabled")

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
        """Append a headline title row with metadata and color tags.

        This mirrors the legacy insertion logic while consolidating
        tag bookkeeping and listbox range calculations within the
        renderer to enable further extraction from AINewsApp.
        """
        color_tag = self.ensure_color_tag(
            row_color or self.app.listbox_default_fg
        )
        prefix_text = f"{display_index}. {localized.title}"
        row_tag = f"row_{len(self.app._row_tag_to_headline)}"

        self.app.listbox.configure(state="normal")
        self.ensure_line_break()
        insertion_index = self.app.listbox.index("end")
        try:
            # Title segment
            self.app.listbox.insert(
                "end",
                prefix_text,
                ("title", color_tag, row_tag),
            )
            # Metadata segment prefixed with a dash for readability
            metadata_with_dash = f" — {metadata_text}"
            self.app.listbox.insert("end", metadata_with_dash, ("metadata", row_tag))
            # Row newline
            self.app.listbox.insert("end", "\n", (row_tag,))
            ranges = self.app.listbox.tag_ranges(row_tag)
            if ranges:
                start_index = str(ranges[0])
            else:
                start_index = str(insertion_index)
            try:
                line_no = int(float(start_index.split(".")[0]))
            except (ValueError, IndexError):
                line_no = int(float(self.app.listbox.index("end-1c").split(".")[0]))
        finally:
            self.app.listbox.configure(state="disabled")

        # Bookkeeping for reverse-lookup and tooltips
        self.app._row_tag_to_headline[row_tag] = original_idx
        self.app._row_tag_to_line[row_tag] = line_no
        self.app._line_to_row_tag[line_no] = row_tag
        self.app._listbox_line_to_headline[line_no] = original_idx
        self.app._listbox_line_details[line_no] = HeadlineTooltipData(
            headline=localized,
            relative_age=relative_label,
            display_index=display_index,
            row_kind="title",
        )
        self.app._listbox_line_prefix[line_no] = len(prefix_text)
        self.app._listbox_line_metadata[line_no] = f" — {metadata_text}"

    def append_message_line(self, text: str) -> None:
        """Append a single message line (fallback text) to the listbox."""
        self.app.listbox.configure(state="normal")
        self.ensure_line_break()
        try:
            self.app.listbox.insert("end", text, ("message",))
            self.app.listbox.insert("end", "\n")
        finally:
            self.app.listbox.configure(state="disabled")


__all__ = ["ListRenderer"]