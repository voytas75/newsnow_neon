"""Toplevel window for article summary rendering (extracted from ui.py).

Updates: v0.52 - 2025-11-18 - Extracted SummaryWindow into ui/windows module.
"""
from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import font
from typing import Callable, List, Optional
from urllib.parse import urlparse
import webbrowser

from ...highlight import HIGHLIGHT_KEYWORDS
from ...models import Headline, SummaryResolution

logger = logging.getLogger(__name__)

SUMMARY_WINDOW_MIN_WIDTH = 780
SUMMARY_WINDOW_MIN_HEIGHT = 600


class SummaryWindow(tk.Toplevel):
    """Toplevel window that renders an article summary."""

    def __init__(
        self,
        master: tk.Tk,
        headline: Headline,
        summary_resolver: Callable[[Headline], SummaryResolution],
    ) -> None:
        super().__init__(master)
        self.headline = headline
        self.article_text: Optional[str] = None
        self.summary_text: Optional[str] = None
        self._summary_resolver = summary_resolver

        self.title(f"Summary • {headline.title}")
        self.configure(bg="black")
        logger.info("Opening summary window for %s", headline.url)

        self._link_url = headline.url
        self._link_color = "#4DA6FF"
        self._link_hover_color = "#80C4FF"

        self.status_var = tk.StringVar(value="Fetching article…")
        self._metadata_font = font.Font(family="Segoe UI", size=9, slant="italic")
        self._current_metadata = self._compose_metadata(
            source=headline.source,
            published_time=headline.published_time,
            published_at=headline.published_at,
            section=headline.section,
            link_updated=False,
        )
        self._summary_text_start = "1.0"

        title_font = font.Font(
            family="Segoe UI", size=14, weight="bold", underline=True
        )
        self.title_label = tk.Label(
            self,
            text=headline.title,
            bg="black",
            fg=self._link_color,
            wraplength=680,
            font=title_font,
            justify="left",
            cursor="hand2",
        )
        self.title_label.pack(padx=20, pady=(20, 6), anchor="w")
        self.title_label.bind("<Button-1>", lambda _event: self._open_article())
        self.title_label.bind("<Enter>", self._on_title_enter)
        self.title_label.bind("<Leave>", self._on_title_leave)

        status_label = tk.Label(
            self, textvariable=self.status_var, bg="black", fg="lightgray"
        )
        status_label.pack(padx=20, pady=(0, 8), anchor="w")

        text_frame = tk.Frame(self, bg="black")
        text_frame.pack(fill="both", expand=True, padx=20, pady=10)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        self.text_widget = tk.Text(
            text_frame,
            wrap="word",
            bg="#101010",
            fg="white",
            insertbackground="white",
            font=("Segoe UI", 12),
            state="disabled",
            yscrollcommand=scrollbar.set,
        )
        self.text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=self.text_widget.yview)

        button_frame = tk.Frame(self, bg="black")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        open_button = tk.Button(
            button_frame,
            text="Open Full Article",
            command=self._open_article,
        )
        open_button.pack(side="left")

        copy_button = tk.Button(
            button_frame, text="Copy Summary", command=self._copy_summary
        )
        copy_button.pack(side="left", padx=10)

        self._apply_initial_geometry()

        threading.Thread(target=self._load_summary, daemon=True).start()

    def _copy_summary(self) -> None:
        if not self.summary_text:
            return
        self.clipboard_clear()
        self.clipboard_append(self.summary_text)
        self.status_var.set("Summary copied to clipboard.")

    def _load_summary(self) -> None:
        try:
            logger.info("Preparing summary for %s", self.headline.url)
            resolution = self._summary_resolver(self.headline)
            self.article_text = resolution.article_text
            self.summary_text = resolution.summary

            source_display = self.headline.source
            link_updated = False
            if resolution.source_url:
                self._link_url = resolution.source_url
                link_updated = resolution.source_url != self.headline.url
                if not source_display:
                    parsed = urlparse(resolution.source_url)
                    domain = parsed.netloc
                    if domain.startswith("www."):
                        domain = domain[4:]
                    source_display = domain or None

            metadata_text = self._compose_metadata(
                source=source_display,
                published_time=self.headline.published_time,
                published_at=self.headline.published_at,
                section=self.headline.section,
                link_updated=link_updated,
            )

            def _update_ui() -> None:
                self._handle_summary_ready(resolution.summary, metadata_text)
                if resolution.from_cache:
                    self.status_var.set("Summary loaded from cache.")
                elif resolution.issue == "article_fetch_failed":
                    self.status_var.set(
                        "Showing fallback summary; article content unavailable."
                    )
                elif resolution.issue == "summary_generation_empty":
                    self.status_var.set(
                        "LLM returned an empty response; showing fallback summary."
                    )
                else:
                    self.status_var.set("Summary ready.")

            self.after(0, _update_ui)
        except Exception as exc:  # pragma: no cover - Async UI errors
            logger.exception("Failed to load summary: %s", exc)

            def _show_error() -> None:
                self._display_error("Unable to load article summary.")

            self.after(0, _show_error)

    def _display_summary(self, summary: str) -> None:
        self._render_text(summary, apply_highlights=True)

    def _display_error(self, message: str) -> None:
        self.status_var.set("Summary unavailable.")
        self._render_text(message, apply_highlights=False)

    def _apply_summary_highlights(self) -> None:
        if not HIGHLIGHT_KEYWORDS:
            return
        widget = getattr(self, "text_widget", None)
        if widget is None or not widget.winfo_exists():
            return
        for tag in list(widget.tag_names()):
            if tag.startswith("highlight_"):
                widget.tag_delete(tag)
        for keyword, color in HIGHLIGHT_KEYWORDS.items():
            if not keyword:
                continue
            tag_name = f"highlight_{keyword.lower()}"
            widget.tag_configure(tag_name, foreground=color)
            start = getattr(self, "_summary_text_start", "1.0")
            while True:
                index = widget.search(keyword, start, tk.END, nocase=True)
                if not index:
                    break
                end_index = f"{index}+{len(keyword)}c"
                existing_tags = widget.tag_names(index)
                if any(tag.startswith("highlight_") for tag in existing_tags):
                    start = end_index
                    continue
                widget.tag_add(tag_name, index, end_index)
                start = end_index

    def _open_article(self) -> None:
        webbrowser.open_new_tab(self._link_url)

    def _on_title_enter(self, _event: tk.Event) -> None:
        self.title_label.config(fg=self._link_hover_color)

    def _on_title_leave(self, _event: tk.Event) -> None:
        self.title_label.config(fg=self._link_color)

    def _compose_metadata(
        self,
        *,
        source: Optional[str],
        published_time: Optional[str],
        published_at: Optional[str],
        section: Optional[str],
        link_updated: bool,
    ) -> str:
        source_text = (source or "").strip() or "Unknown source"

        parts: List[str] = [f"Source: {source_text}"]

        time_text = (published_time or "").strip()
        iso_text = (published_at or "").strip()
        if time_text and iso_text:
            parts.append(f"Published: {time_text} ({iso_text})")
        elif time_text:
            parts.append(f"Published: {time_text}")
        elif iso_text:
            parts.append(f"Published: {iso_text}")

        section_text = (section or "").strip()
        if section_text:
            parts.append(f"Section: {section_text}")

        if link_updated:
            parts.append("Link updated to direct article")

        return " | ".join(parts)

    def _handle_summary_ready(self, summary: str, metadata_text: str) -> None:
        self._current_metadata = metadata_text
        self._display_summary(summary)

    def _apply_initial_geometry(self) -> None:
        """Size the window so action buttons stay visible even on dense layouts."""
        self.update_idletasks()
        required_width = max(self.winfo_reqwidth(), SUMMARY_WINDOW_MIN_WIDTH)
        required_height = max(self.winfo_reqheight(), SUMMARY_WINDOW_MIN_HEIGHT)
        self.minsize(required_width, required_height)
        self.geometry(f"{required_width}x{required_height}")

    def _render_text(self, body: str, *, apply_highlights: bool) -> None:
        """Render metadata and body text into the summary text widget."""
        metadata = (self._current_metadata or "").strip()
        if not self.text_widget.winfo_exists():
            return
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self._summary_text_start = "1.0"
        if metadata:
            tag_name = "summary_metadata"
            self.text_widget.tag_configure(
                tag_name,
                font=self._metadata_font,
                foreground="#A9A9A9",
            )
            self.text_widget.insert("end", f"{metadata}\n\n", (tag_name,))
            self._summary_text_start = self.text_widget.index("end")
        self.text_widget.insert("end", body)
        if apply_highlights:
            self._apply_summary_highlights()
        self.text_widget.config(state="disabled")


__all__ = ["SummaryWindow"]