"""Tkinter UI components for the NewsNow Neon application.

These classes were migrated from the legacy ``legacy_app.py`` script (formerly
``newsnow_neon.py``) so the
core package owns the ticker widgets, summary window, diagnostics dialogs, and
other presentation logic.

Updates: v0.50 - 2025-01-07 - Extracted Tk UI classes from the legacy script into the package.
Updates: v0.51 - 2025-10-29 - Stabilized ticker repositioning to prevent headline overlap.
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from datetime import datetime, timezone, tzinfo
from tkinter import font
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union
from urllib.parse import urlparse
import webbrowser

from .config import DEFAULT_COLOR_PROFILE
from .highlight import (
    HEATMAP_FALLBACK_COLOR,
    HIGHLIGHT_KEYWORDS,
    blend_hex,
    build_keyword_heatmap_data,
    compose_headline_tooltip,
    highlight_segments,
    relative_luminance,
)
from .models import (
    AppMetadata,
    Headline,
    HoverTooltip,
    KeywordHeatmapData,
    RedisStatistics,
    SummaryResolution,
)

if TYPE_CHECKING:  # pragma: no cover - type checking import only
    from .app import AINewsApp

logger = logging.getLogger(__name__)

SUMMARY_WINDOW_MIN_WIDTH = 780
SUMMARY_WINDOW_MIN_HEIGHT = 600


class NewsTicker(tk.Canvas):
    """Marquee-style ticker widget with hover pause and clickable headlines."""

    def __init__(
        self,
        master: tk.Misc,
        speed: int = 2,
        *,
        max_title_length: Optional[int] = 30,
        font_spec: tuple[str, int, str] = ("Consolas", 16, "bold"),
        item_spacing: int = 60,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            bg=DEFAULT_COLOR_PROFILE["background"],
            height=50,
            highlightthickness=0,
            **kwargs,
        )
        self.speed = speed
        self.item_spacing = item_spacing
        self.text_color = DEFAULT_COLOR_PROFILE["text"]
        self.hover_color = DEFAULT_COLOR_PROFILE.get("hover", self.text_color)
        self.bg_color = DEFAULT_COLOR_PROFILE["background"]
        self.headline_order: List[str] = []
        self.hover_group_tag: Optional[str] = None
        self._headline_groups: Dict[str, Dict[str, Any]] = {}
        self._segment_to_group: Dict[int, str] = {}
        self.is_hovered = False
        self.max_title_length = max_title_length
        self.font = font_spec
        self._font_metrics = font.Font(self, font=self.font)
        self._tooltip = HoverTooltip(self, wraplength=520)

        self.message_item = self.create_text(
            self.winfo_reqwidth(),
            25,
            text="Loading AI headlines…",
            fill=self.text_color,
            font=self.font,
            anchor="w",
            tags=("message",),
        )

        self.bind("<Configure>", self._reset_position)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Button-1>", self._on_click)

        self.apply_color_profile(DEFAULT_COLOR_PROFILE)
        self._reset_position()
        self._animate()

    def set_text(self, text: str) -> None:
        """Display a non-interactive message."""
        self.delete("headline")
        self._reset_groups()
        self.itemconfigure(self.message_item, text=text, fill=self.text_color, state="normal")
        self.configure(cursor="arrow")
        self._reset_position()
        self._tooltip.hide()

    def set_items(self, items: Sequence[Union[Headline, Mapping[str, str]]]) -> None:
        """Populate the ticker with interactive headlines."""
        self.delete("headline")
        self._reset_groups()
        self._clear_hover()

        normalized: List[Headline] = []
        for entry in items:
            if isinstance(entry, Headline):
                normalized.append(entry)
            elif isinstance(entry, Mapping):
                candidate = Headline.from_dict(dict(entry))
                if candidate is not None:
                    normalized.append(candidate)
        filtered = [item for item in normalized if item.title and item.url]
        if not filtered:
            self.itemconfigure(
                self.message_item,
                text="No headlines available right now.",
                fill=self.text_color,
                state="normal",
            )
            self.configure(cursor="arrow")
            self._reset_position()
            return

        limit = min(15, len(filtered))
        for entry in filtered[:limit]:
            self._create_headline_group(entry)

        if not self.headline_order:
            self.itemconfigure(
                self.message_item,
                text="No headlines available right now.",
                fill=self.text_color,
                state="normal",
            )
            self.configure(cursor="arrow")
            self._reset_position()
            return

        self.itemconfigure(self.message_item, state="hidden")
        self.after_idle(self._ensure_positions)
        self.configure(cursor="arrow")

    def set_speed(self, speed: int) -> None:
        """Update scroll speed while keeping a sane lower bound."""

        try:
            value = int(speed)
        except (TypeError, ValueError):
            logger.debug("Invalid ticker speed '%s'; keeping previous value %s", speed, self.speed)
            return
        self.speed = max(1, value)

    def apply_color_profile(self, profile: Mapping[str, str]) -> None:
        background = profile.get("background", "black")
        text = profile.get("text", "white")
        hover = profile.get("hover", text)
        self.configure(bg=background)
        self.bg_color = background
        self.text_color = text
        self.hover_color = hover
        self.itemconfigure("headline", fill=text)
        self.itemconfigure(self.message_item, fill=text)
        self._tooltip.background = background
        self._tooltip.foreground = text

    def set_colors(self, *, background: str, text: str) -> None:
        self.apply_color_profile({"background": background, "text": text, "hover": self.hover_color})

    def _ensure_positions(self) -> None:
        """Align headline items horizontally starting at the right edge."""
        if not self.headline_order:
            return
        y = max(self.winfo_height() // 2, 25)
        x = float(self.winfo_width())
        for group_tag in self.headline_order:
            group = self._headline_groups.get(group_tag)
            if not group:
                continue
            offsets = group["offsets"]
            items = group["items"]
            for idx, item_id in enumerate(items):
                offset = offsets[idx] if idx < len(offsets) else 0.0
                self.coords(item_id, x + offset, y)
            width = group.get("width", 0.0)
            x += width + self.item_spacing

    def _reset_position(self, *_args: object) -> None:
        self.coords(self.message_item, self.winfo_width(), max(self.winfo_height() // 2, 25))
        self._ensure_positions()

    def _reset_groups(self) -> None:
        self.headline_order.clear()
        self.hover_group_tag = None
        self._headline_groups.clear()
        self._segment_to_group.clear()
        self._tooltip.hide()

    def _create_headline_group(self, headline: Headline) -> None:
        title = headline.title.strip()
        if not title:
            return
        display_title = title
        if self.max_title_length and self.max_title_length > 3 and len(display_title) > self.max_title_length:
            display_title = display_title[: self.max_title_length - 3].rstrip() + "…"

        group_tag = f"headline_group_{len(self.headline_order)}"
        segments = highlight_segments(display_title)
        items: List[int] = []
        base_colors: Dict[int, str] = {}
        defaults: set[int] = set()
        offsets: List[float] = []
        origin_x = float(self.winfo_width())
        x_cursor = origin_x
        y = max(self.winfo_height() // 2, 25)

        for segment_text, highlight_color in segments:
            if not segment_text:
                continue
            color = highlight_color or self.text_color
            item_id = self.create_text(
                x_cursor,
                y,
                text=segment_text,
                fill=color,
                font=self.font,
                anchor="w",
                tags=("headline", group_tag),
            )
            bbox = self.bbox(item_id)
            width = float((bbox[2] - bbox[0]) if bbox else self._measure_segment_width(segment_text))
            items.append(item_id)
            base_colors[item_id] = color
            if highlight_color is None:
                defaults.add(item_id)
            self._segment_to_group[item_id] = group_tag
            offsets.append(x_cursor - origin_x)
            x_cursor += width

        if not items:
            for orphan in items:
                self.delete(orphan)
            return

        group_width = max(x_cursor - origin_x, 0.0)
        self._headline_groups[group_tag] = {
            "url": headline.url,
            "items": items,
            "base_colors": base_colors,
            "defaults": defaults,
            "offsets": offsets,
            "width": group_width,
            "headline": headline,
            "full_title": title,
            "display_title": display_title,
        }
        self.headline_order.append(group_tag)

    def _measure_segment_width(self, text: str) -> float:
        if not text:
            return 0.0
        try:
            return float(self._font_metrics.measure(text))
        except tk.TclError:
            self._font_metrics = font.Font(self, font=self.font)
            return float(self._font_metrics.measure(text))

    def _animate(self) -> None:
        if self.is_hovered:
            self.after(50, self._animate)
            return
        for group_tag in self.headline_order:
            group = self._headline_groups.get(group_tag)
            if not group:
                continue
            items = group.get("items", [])
            if not items:
                continue
            for item_id in items:
                self.move(item_id, -self.speed, 0)
            coords = [self.coords(item_id) for item_id in items]
            if coords and all(coord and coord[0] < -self.item_spacing for coord in coords):
                base_x = float(self.winfo_width()) + self.item_spacing
                relative_offsets = group.get("offsets", ())
                default_y = max(self.winfo_height() // 2, 25)
                for idx, item_id in enumerate(items):
                    offset = relative_offsets[idx] if idx < len(relative_offsets) else 0.0
                    coord = coords[idx] if idx < len(coords) else None
                    y_pos = coord[1] if coord else default_y
                    self.coords(item_id, base_x + offset, y_pos)
        self.after(50, self._animate)

    def _on_enter(self, _event: tk.Event) -> None:
        self.is_hovered = True

    def _on_leave(self, _event: tk.Event) -> None:
        self.is_hovered = False
        self._clear_hover()

    def _on_motion(self, event: tk.Event) -> None:
        current = self.find_withtag("current")
        if not current:
            self._clear_hover()
            return
        group_tag = self._segment_to_group.get(current[0])
        if not group_tag:
            self._clear_hover()
            return
        self._set_hover(group_tag)
        self._show_tooltip_for_group(group_tag, event)

    def _on_click(self, _event: tk.Event) -> None:
        target_group = self.hover_group_tag
        if target_group is None:
            current = self.find_withtag("current")
            if current:
                target_group = self._segment_to_group.get(current[0])
        if target_group:
            url = self._headline_groups.get(target_group, {}).get("url")
            if url:
                webbrowser.open_new_tab(url)
        self._tooltip.hide()

    def _set_hover(self, group_tag: str) -> None:
        self._clear_hover()
        group = self._headline_groups.get(group_tag)
        if not group:
            return
        self.hover_group_tag = group_tag
        for item_id in group.get("items", []):
            self.itemconfigure(item_id, fill=self.hover_color)

    def _clear_hover(self) -> None:
        if not self.hover_group_tag:
            return
        group = self._headline_groups.get(self.hover_group_tag)
        if not group:
            self.hover_group_tag = None
            self._tooltip.hide()
            return
        base_colors: Mapping[int, str] = group.get("base_colors", {})
        for item_id in group.get("items", []):
            base_color = base_colors.get(item_id, self.text_color)
            self.itemconfigure(item_id, fill=base_color)
        self.hover_group_tag = None
        self._tooltip.hide()

    def _show_tooltip_for_group(self, group_tag: str, event: tk.Event) -> None:
        group = self._headline_groups.get(group_tag)
        if not group:
            self._tooltip.hide()
            return
        headline = group.get("headline")
        if isinstance(headline, Headline):
            tooltip_text = compose_headline_tooltip(headline)
            self._tooltip.show(tooltip_text, event.x_root, event.y_root)
        else:
            self._tooltip.hide()


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

        title_font = font.Font(family="Segoe UI", size=14, weight="bold", underline=True)
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


class KeywordHeatmapWindow(tk.Toplevel):
    """Visualise keyword frequency across sections using a heatmap."""

    def __init__(
        self,
        master: "AINewsApp",
        headlines: Sequence[Headline],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._on_close_callback = on_close
        self._data: Optional[KeywordHeatmapData] = None
        self.configure(bg="black")
        self.title("Keyword Frequency Heatmap")
        self.resizable(True, True)

        self.info_var = tk.StringVar(value="")
        info_label = tk.Label(
            self,
            textvariable=self.info_var,
            bg="black",
            fg="#89CFF0",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify="left",
        )
        info_label.pack(fill="x", padx=16, pady=(16, 4))

        self.canvas = tk.Canvas(
            self,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self.legend_var = tk.StringVar(value="")
        legend_label = tk.Label(
            self,
            textvariable=self.legend_var,
            bg="black",
            fg="lightgray",
            justify="left",
            wraplength=600,
        )
        legend_label.pack(fill="x", padx=16, pady=(0, 8))

        button_row = tk.Frame(self, bg="black")
        button_row.pack(fill="x", padx=16, pady=(0, 16))
        close_button = tk.Button(button_row, text="Close", command=self._handle_close)
        close_button.pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._handle_close)
        self.bind("<Escape>", lambda _event: self._handle_close())

        self.update_data(headlines)

    def update_data(self, headlines: Sequence[Headline]) -> None:
        """Recompute and redraw the heatmap from the provided headlines."""

        self.canvas.delete("all")
        dataset = build_keyword_heatmap_data(headlines)
        self._data = dataset

        if dataset is None:
            self.info_var.set("No keyword matches found in current headlines.")
            self.legend_var.set(
                "Tip: adjust highlight keywords in Settings or via NEWS_HIGHLIGHT_KEYWORDS to track additional terms."
            )
            width, height = 480, 220
            self.canvas.config(width=width, height=height)
            self.canvas.create_text(
                width / 2,
                height / 2,
                text="No keyword data available to plot.",
                fill="#CCCCCC",
                font=("Segoe UI", 12),
            )
            return

        total_headlines = sum(dataset.totals.values())
        sections_count = len(dataset.sections)
        keywords_count = len(dataset.keywords)
        self.info_var.set(
            f"{total_headlines} headlines • {sections_count} sections • {keywords_count} keywords"
        )
        max_percent = dataset.max_density * 100.0
        self.legend_var.set(
            "Color intensity reflects the share of section headlines containing each keyword "
            f"(maximum {max_percent:.1f}% in this sample)."
        )

        self._render_heatmap(dataset)

    def _render_heatmap(self, dataset: KeywordHeatmapData) -> None:
        keywords = dataset.keywords
        sections = dataset.sections
        if not keywords or not sections:
            return

        padding_x = 24
        padding_y = 30
        header_height = 58
        cell_width = 130
        cell_height = 60

        max_section_name = max(len(section) for section in sections)
        label_col_width = max(150, min(240, max_section_name * 9))

        canvas_width = padding_x * 2 + label_col_width + len(keywords) * cell_width
        canvas_height = padding_y * 2 + header_height + len(sections) * cell_height

        self.canvas.config(
            width=canvas_width,
            height=canvas_height,
            scrollregion=(0, 0, canvas_width, canvas_height),
        )

        header_center_y = padding_y + header_height / 2
        for column, keyword in enumerate(keywords):
            x = padding_x + label_col_width + column * cell_width + (cell_width / 2)
            self.canvas.create_text(
                x,
                header_center_y,
                text=keyword,
                fill="#E0E0E0",
                font=("Segoe UI", 11, "bold"),
                width=cell_width - 12,
            )

        for row, section in enumerate(sections):
            y = padding_y + header_height + row * cell_height + (cell_height / 2)
            self.canvas.create_text(
                padding_x + label_col_width / 2,
                y,
                text=section,
                fill="#E0E0E0",
                font=("Segoe UI", 10, "bold"),
                width=label_col_width - 12,
            )

        max_density = max(dataset.max_density, 1e-9)
        base_color = "#101820"

        for row, section in enumerate(sections):
            total = max(dataset.totals.get(section, 0), 1)
            y0 = padding_y + header_height + row * cell_height
            y1 = y0 + cell_height
            row_counts = dataset.counts.get(section, {})
            for column, keyword in enumerate(keywords):
                x0 = padding_x + label_col_width + column * cell_width
                x1 = x0 + cell_width
                count = row_counts.get(keyword, 0)
                density = count / total
                intensity = density / max_density if max_density > 0 else 0.0
                fill_color = blend_hex(
                    base_color,
                    dataset.keyword_colors.get(keyword, HEATMAP_FALLBACK_COLOR),
                    intensity,
                )
                self.canvas.create_rectangle(
                    x0,
                    y0,
                    x1,
                    y1,
                    fill=fill_color,
                    outline="#2F2F2F",
                    width=1,
                )
                percent_value = density * 100.0
                percent_text = (
                    f"{percent_value:.1f}%"
                    if percent_value < 5.0
                    else f"{percent_value:.0f}%"
                )
                label_text = f"{count} hits\n{percent_text}"
                text_color = (
                    "#0F0F0F" if relative_luminance(fill_color) > 180 else "#F5F5F5"
                )
                self.canvas.create_text(
                    x0 + (cell_width / 2),
                    y0 + (cell_height / 2),
                    text=label_text,
                    fill=text_color,
                    font=("Segoe UI", 10, "bold"),
                )

    def _handle_close(self) -> None:
        if self._on_close_callback:
            try:
                self._on_close_callback()
            except Exception:  # pragma: no cover - safeguard
                logger.exception("Error running heatmap close callback.")
        self.destroy()


class RedisStatsWindow(tk.Toplevel):
    """Display current Redis cache metrics and payload insight."""

    def __init__(
        self,
        master: "AINewsApp",
        stats: RedisStatistics,
        timezone_name: str,
        timezone_obj: tzinfo,
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._on_close = on_close
        self._timezone_name = timezone_name
        self._timezone = timezone_obj
        self._closed = False

        self.title("Redis Cache Statistics")
        self.configure(bg="black")
        self.resizable(False, False)
        self.transient(master)
        self.geometry("560x560")
        self.protocol("WM_DELETE_WINDOW", self._handle_close)
        self.bind("<Escape>", lambda _event: self._handle_close())

        header = tk.Label(
            self,
            text="Redis diagnostics",
            font=("Segoe UI", 14, "bold"),
            bg="black",
            fg="white",
        )
        header.pack(pady=(16, 6))

        subtitle = tk.Label(
            self,
            text=f"Timezone: {timezone_name}",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10),
        )
        subtitle.pack(pady=(0, 12))

        info_frame = tk.Frame(self, bg="black")
        info_frame.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        self._field_order = [
            "Cache key",
            "Key present",
            "Headlines",
            "Sections",
            "Sources",
            "Summaries",
            "Ticker text",
            "TTL",
            "Payload size",
            "Latest headline",
            "Latest headline timestamp",
            "Historical snapshots",
            "Latest snapshot key",
            "Redis version",
            "Connected clients",
            "Database keys",
            "Used memory",
        ]
        self._field_vars: Dict[str, tk.StringVar] = {}
        for label_text in self._field_order:
            var = tk.StringVar(value="…")
            self._add_row(info_frame, label_text, var)
            self._field_vars[label_text] = var

        warnings_label = tk.Label(
            info_frame,
            text="Warnings",
            bg="black",
            fg="#FFA94D",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        warnings_label.pack(fill="x", pady=(12, 2))

        self._warnings_var = tk.StringVar(value="No warnings.")
        warnings_value = tk.Label(
            info_frame,
            textvariable=self._warnings_var,
            bg="black",
            fg="#FFCD94",
            justify="left",
            wraplength=500,
            anchor="w",
        )
        warnings_value.pack(fill="x")

        button_row = tk.Frame(self, bg="black")
        button_row.pack(fill="x", padx=18, pady=(0, 18))
        close_btn = tk.Button(button_row, text="Close", command=self._handle_close)
        close_btn.pack(side="right")

        self.update_stats(stats)

    def _add_row(
        self, container: tk.Frame, label_text: str, value_var: tk.StringVar
    ) -> None:
        row = tk.Frame(container, bg="black")
        row.pack(fill="x", pady=2)
        label = tk.Label(
            row,
            text=f"{label_text}:",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10, "bold"),
            width=24,
            anchor="w",
        )
        label.pack(side="left")
        value_label = tk.Label(
            row,
            textvariable=value_var,
            bg="black",
            fg="white",
            justify="left",
            wraplength=420,
            anchor="w",
        )
        value_label.pack(fill="x", expand=True, side="left")

    def update_stats(self, stats: RedisStatistics) -> None:
        values = self._format_values(stats)
        for label_text, value in values.items():
            if label_text in self._field_vars:
                self._field_vars[label_text].set(value)
        warnings_text = "No warnings."
        if stats.warnings:
            warnings_text = "\n".join(stats.warnings)
        self._warnings_var.set(warnings_text)

    def _format_values(self, stats: RedisStatistics) -> Dict[str, str]:
        latest_timestamp = self._format_latest_timestamp(stats)
        return {
            "Cache key": stats.cache_key,
            "Key present": self._format_bool(stats.key_present),
            "Headlines": f"{stats.headline_count}",
            "Sections": self._format_sequence(stats.sections),
            "Sources": self._format_sequence(stats.sources),
            "Summaries": f"{stats.summary_count}",
            "Ticker text": "Present" if stats.ticker_present else "Absent",
            "TTL": self._format_ttl(stats),
            "Payload size": self._format_bytes(stats.payload_bytes),
            "Latest headline": self._format_latest_headline(stats),
            "Latest headline timestamp": latest_timestamp,
            "Historical snapshots": str(stats.historical_snapshot_count),
            "Latest snapshot key": stats.latest_snapshot_key or "n/a",
            "Redis version": stats.redis_version or "n/a",
            "Connected clients": (
                str(stats.connected_clients) if stats.connected_clients is not None else "n/a"
            ),
            "Database keys": str(stats.dbsize) if stats.dbsize is not None else "n/a",
            "Used memory": stats.used_memory_human or "n/a",
        }

    def _format_ttl(self, stats: RedisStatistics) -> str:
        if not stats.key_present:
            return "Key missing"
        if stats.ttl_seconds is None:
            return "No expiration"
        if stats.ttl_seconds < 0:
            return "Expired"
        return f"{stats.ttl_seconds}s ({self._humanise_seconds(stats.ttl_seconds)})"

    @staticmethod
    def _format_sequence(items: Sequence[str]) -> str:
        if not items:
            return "n/a"
        if len(items) <= 6:
            return ", ".join(items)
        preview = ", ".join(items[:6])
        remainder = len(items) - 6
        return f"{preview}, +{remainder} more"

    @staticmethod
    def _format_bool(value: bool) -> str:
        return "Yes" if value else "No"

    @staticmethod
    def _humanise_seconds(seconds: int) -> str:
        if seconds <= 0:
            return "0s"
        remainder = seconds
        parts: List[str] = []
        days, remainder = divmod(remainder, 86_400)
        if days:
            parts.append(f"{days}d")
        hours, remainder = divmod(remainder, 3_600)
        if hours:
            parts.append(f"{hours}h")
        minutes, remainder = divmod(remainder, 60)
        if minutes:
            parts.append(f"{minutes}m")
        if remainder or not parts:
            parts.append(f"{remainder}s")
        return " ".join(parts)

    @staticmethod
    def _format_bytes(value: Optional[int]) -> str:
        if value is None or value < 0:
            return "n/a"
        units = ["B", "KiB", "MiB", "GiB", "TiB"]
        size = float(value)
        for index, unit in enumerate(units):
            if size < 1024.0 or index == len(units) - 1:
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TiB"

    def _format_latest_headline(self, stats: RedisStatistics) -> str:
        if not stats.latest_headline_title:
            return "n/a"
        title = stats.latest_headline_title.strip()
        if len(title) > 90:
            title = title[:87] + "…"
        if stats.latest_headline_source:
            return f"{title} ({stats.latest_headline_source})"
        return title

    def _format_latest_timestamp(self, stats: RedisStatistics) -> str:
        timestamp = stats.latest_headline_time
        if timestamp is None:
            return "n/a"
        local_dt = timestamp.astimezone(self._timezone)
        age_seconds = max(
            0, int((datetime.now(timezone.utc) - timestamp).total_seconds())
        )
        age_label = self._humanise_seconds(age_seconds)
        formatted = local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        return f"{formatted} ({age_label} ago)"

    def _handle_close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._on_close:
            try:
                self._on_close()
            except Exception:  # pragma: no cover - safeguard
                logger.exception("Error running Redis stats close callback.")
        self.destroy()


class AppInfoWindow(tk.Toplevel):
    """Display application metadata and a system snapshot."""

    def __init__(
        self,
        master: "AINewsApp",
        metadata: AppMetadata,
        system_rows: Sequence[Tuple[str, str]],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._on_close = on_close
        self._on_close_invoked = False

        self.title(f"About {metadata.name}")
        self.configure(bg="black")
        self.resizable(False, False)
        self.transient(master)
        self.geometry("480x420")
        self.protocol("WM_DELETE_WINDOW", self._handle_close)
        self.bind("<Escape>", lambda _event: self._handle_close())

        title_label = tk.Label(
            self,
            text=metadata.name,
            font=("Segoe UI", 16, "bold"),
            bg="black",
            fg="white",
        )
        title_label.pack(pady=(18, 4))

        version_label = tk.Label(
            self,
            text=f"Version {metadata.version}",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10),
        )
        version_label.pack()

        description_label = tk.Label(
            self,
            text=metadata.description,
            bg="black",
            fg="lightgray",
            wraplength=420,
            justify="left",
            font=("Segoe UI", 10),
        )
        description_label.pack(padx=20, pady=(6, 14))

        info_frame = tk.Frame(self, bg="black")
        info_frame.pack(fill="x", padx=20)

        for label_text, value_text in system_rows:
            self._add_kv_row(info_frame, label_text, value_text)

        self._add_kv_row(info_frame, "Author", metadata.author)

        support_row = tk.Frame(info_frame, bg="black")
        support_row.pack(fill="x", pady=(6, 2))
        support_label = tk.Label(
            support_row,
            text="Support:",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10, "bold"),
        )
        support_label.pack(side="left")

        if metadata.donate_url:
            link_color = "#4DA6FF"
            donate_label = tk.Label(
                support_row,
                text=metadata.donate_url,
                bg="black",
                fg=link_color,
                cursor="hand2",
                wraplength=320,
                justify="left",
                font=("Segoe UI", 10),
            )
            donate_label.pack(side="left", padx=(8, 0))
            donate_label.bind(
                "<Button-1>",
                lambda _event, url=metadata.donate_url: webbrowser.open_new_tab(url),
            )
            donate_label.bind(
                "<Enter>",
                lambda _event, widget=donate_label: widget.config(fg="#80C4FF"),
            )
            donate_label.bind(
                "<Leave>",
                lambda _event, widget=donate_label: widget.config(fg=link_color),
            )
        else:
            fallback_label = tk.Label(
                support_row,
                text="Set NEWSNOW_DONATE_URL to share a donation link.",
                bg="black",
                fg="lightgray",
                wraplength=320,
                justify="left",
                font=("Segoe UI", 10),
            )
            fallback_label.pack(side="left", padx=(8, 0))

        button_frame = tk.Frame(self, bg="black")
        button_frame.pack(fill="x", padx=20, pady=(16, 18))
        close_button = tk.Button(button_frame, text="Close", command=self._handle_close)
        close_button.pack(side="right")
        close_button.focus_set()

    def _add_kv_row(self, container: tk.Misc, key: str, value: str) -> None:
        row = tk.Frame(container, bg="black")
        row.pack(fill="x", pady=2)
        key_label = tk.Label(
            row,
            text=f"{key}:",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10, "bold"),
            width=18,
            anchor="w",
        )
        key_label.pack(side="left")
        value_label = tk.Label(
            row,
            text=value,
            bg="black",
            fg="white",
            wraplength=320,
            justify="left",
            anchor="w",
        )
        value_label.pack(fill="x", padx=(8, 0))

    def _handle_close(self) -> None:
        if self._on_close_invoked:
            return
        self._on_close_invoked = True
        if self._on_close:
            try:
                self._on_close()
            except Exception:  # pragma: no cover - safeguard
                logger.exception("Error running app info close callback.")
        self.destroy()


__all__ = [
    "NewsTicker",
    "SummaryWindow",
    "KeywordHeatmapWindow",
    "RedisStatsWindow",
    "AppInfoWindow",
]
