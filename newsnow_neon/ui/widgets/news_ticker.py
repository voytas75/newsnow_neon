"""Marquee-style ticker widget module extracted from ui.py."""
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import font
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union
import webbrowser

from ...config import DEFAULT_COLOR_PROFILE
from ...highlight import compose_headline_tooltip, highlight_segments
from ...models import Headline, HoverTooltip

logger = logging.getLogger(__name__)


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
        self._spawn_measure_cache: Dict[str, float] = {}
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
        y = float(max(self.winfo_height() // 2, 25))
        x = float(self.winfo_width())
        for group_tag in self.headline_order:
            group = self._headline_groups.get(group_tag)
            if not group:
                continue
            self._place_group(group_tag, x, default_y=y)
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
        self._spawn_measure_cache.clear()
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
        cached = self._spawn_measure_cache.get(text)
        if cached is not None:
            return cached
        try:
            width = float(self._font_metrics.measure(text))
        except tk.TclError:
            self._font_metrics = font.Font(self, font=self.font)
            width = float(self._font_metrics.measure(text))
        self._spawn_measure_cache[text] = width
        return width

    def _place_group(
        self,
        group_tag: str,
        origin_x: float,
        *,
        y_values: Optional[Sequence[Optional[float]]] = None,
        default_y: Optional[float] = None,
    ) -> None:
        group = self._headline_groups.get(group_tag)
        if not group:
            return
        items = group.get("items", [])
        offsets = group.get("offsets", [])
        if default_y is None:
            default_y = float(max(self.winfo_height() // 2, 25))
        for idx, item_id in enumerate(items):
            offset = offsets[idx] if idx < len(offsets) else 0.0
            y_coord: float
            if y_values is not None and idx < len(y_values) and y_values[idx] is not None:
                y_coord = float(y_values[idx])  # reuse existing vertical alignment
            else:
                current_coords = self.coords(item_id)
                if current_coords:
                    y_coord = float(current_coords[1])
                else:
                    y_coord = default_y
            self.coords(item_id, origin_x + offset, y_coord)

    def _compute_rightmost_edge(self, *, exclude: Optional[str] = None) -> float:
        rightmost = float(self.winfo_width())
        for group_tag in self.headline_order:
            if group_tag == exclude:
                continue
            group = self._headline_groups.get(group_tag)
            if not group:
                continue
            for item_id in group.get("items", []):
                bbox = self.bbox(item_id)
                if bbox:
                    rightmost = max(rightmost, float(bbox[2]))
        return rightmost

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
                y_values = [coord[1] if coord else None for coord in coords]
                spawn_origin = max(
                    float(self.winfo_width()),
                    self._compute_rightmost_edge(exclude=group_tag),
                ) + self.item_spacing
                self._place_group(group_tag, spawn_origin, y_values=y_values)
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


__all__ = ["NewsTicker"]