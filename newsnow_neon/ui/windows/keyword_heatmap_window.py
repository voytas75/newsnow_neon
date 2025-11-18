"""Keyword heatmap window extracted from ui.py.

Updates: v0.52 - 2025-11-18 - Extracted KeywordHeatmapWindow into ui/windows.
"""
from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable, Optional, Sequence, List

from ...highlight import (
    HEATMAP_FALLBACK_COLOR,
    blend_hex,
    build_keyword_heatmap_data,
    relative_luminance,
)
from ...models import Headline, KeywordHeatmapData

logger = logging.getLogger(__name__)


class KeywordHeatmapWindow(tk.Toplevel):
    """Visualise keyword frequency across sections using a heatmap."""

    def __init__(
        self,
        master: tk.Misc,
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

        canvas_container = tk.Frame(self, bg="black")
        canvas_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        canvas_container.rowconfigure(0, weight=1)
        canvas_container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_container,
            bg="black",
            highlightthickness=0,
            xscrollincrement=10,
            yscrollincrement=10,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.v_scrollbar = tk.Scrollbar(
            canvas_container,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")

        self.h_scrollbar = tk.Scrollbar(
            canvas_container,
            orient="horizontal",
            command=self.canvas.xview,
        )
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set,
        )

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        self.canvas.bind("<Shift-Button-4>", self._on_shift_mousewheel)
        self.canvas.bind("<Shift-Button-5>", self._on_shift_mousewheel)

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
            self._configure_canvas_viewport(width, height)
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
        summary_bits = [
            f"{total_headlines} headlines",
            f"{sections_count} sections",
            f"{keywords_count} keywords",
        ]
        if keywords_count > 8:
            summary_bits.append("scroll to explore")
        self.info_var.set(" • ".join(summary_bits))
        max_percent = dataset.max_density * 100.0
        legend_parts = [
            "Color intensity reflects the share of section headlines containing each keyword",
            f"(maximum {max_percent:.1f}% in this sample).",
        ]
        if keywords_count > 6 or sections_count > 8:
            legend_parts.append(
                "Use the scrollbars or Shift+mouse wheel to navigate through the heatmap."
            )
        self.legend_var.set(" ".join(legend_parts))

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

        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

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
                    "#0F0F0F"
                    if relative_luminance(fill_color) > 180
                    else "#F5F5F5"
                )
                self.canvas.create_text(
                    x0 + (cell_width / 2),
                    y0 + (cell_height / 2),
                    text=label_text,
                    fill=text_color,
                    font=("Segoe UI", 10, "bold"),
                )

        self._configure_canvas_viewport(canvas_width, canvas_height)

    def _configure_canvas_viewport(self, width: int, height: int) -> None:
        viewport_width = max(min(width, 960), 360)
        viewport_height = max(min(height, 640), 320)
        self.canvas.config(
            width=viewport_width,
            height=viewport_height,
            scrollregion=(0, 0, width, height),
        )
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)

    def _on_mousewheel(self, event: tk.Event) -> str:
        delta = 0
        if hasattr(event, "delta") and event.delta:
            delta = int(-event.delta / 120)
        elif getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        if delta:
            self.canvas.yview_scroll(delta, "units")
        return "break"

    def _on_shift_mousewheel(self, event: tk.Event) -> str:
        delta = 0
        if hasattr(event, "delta") and event.delta:
            delta = int(-event.delta / 120)
        elif getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        if delta:
            self.canvas.xview_scroll(delta, "units")
        return "break"

    def _handle_close(self) -> None:
        if self._on_close_callback:
            try:
                self._on_close_callback()
            except Exception:  # pragma: no cover - safeguard
                logger.exception("Error running heatmap close callback.")
        self.destroy()


__all__ = ["KeywordHeatmapWindow"]