"""Highlight keywords controller.

Updates: v0.52 - 2025-11-18 - Minimal wrapper for keyword application.
"""
from __future__ import annotations
import logging
import tkinter as tk
from tkinter import messagebox
from ...highlight import (
    ENV_HIGHLIGHT_KEYWORDS,
    apply_highlight_keywords,
    parse_highlight_keywords,
    has_highlight_pattern,
)


class HighlightController:
    """Manages highlight keywords and related UI state."""

    def __init__(self, app) -> None:
        self.app = app

    def update_heatmap_button_state(self) -> None:
        if not hasattr(self.app, "heatmap_btn"):
            return
        state = tk.NORMAL if has_highlight_pattern() else tk.DISABLED
        try:
            self.app.heatmap_btn.config(state=state)
        except Exception:  # pragma: no cover - Tk reconfigure issue
            logging.getLogger(__name__).debug(
                "Unable to update heatmap button state."
            )
        if (
            state == tk.DISABLED
            and getattr(self.app, "_heatmap_window", None)
            and self.app._heatmap_window.winfo_exists()
        ):
            try:
                self.app._heatmap_window.destroy()
            finally:
                self.app._heatmap_window = None

    def refresh_views_for_update(self) -> None:
        if not hasattr(self.app, "_raw_headlines"):
            return
        self.app._render_filtered_headlines(
            reschedule=False,
            log_status=False,
            update_tickers=False,
        )
        if getattr(self.app, "_heatmap_window", None) and self.app._heatmap_window.winfo_exists():
            if not has_highlight_pattern():
                try:
                    self.app._heatmap_window.destroy()
                finally:
                    self.app._heatmap_window = None
            else:
                self.app._heatmap_window.update_data(self.app.headlines)
        self.app._update_status_summary()

    def update_keywords_setting(
        self,
        raw_value: str,
        *,
        refresh_views: bool,
        persist: bool,
        show_feedback: bool,
    ) -> None:
        candidate = raw_value.strip() if isinstance(raw_value, str) else ""
        if candidate:
            parsed = parse_highlight_keywords(
                candidate,
                ENV_HIGHLIGHT_KEYWORDS,
                allow_empty_fallback=False,
            )
            if not parsed:
                if show_feedback:
                    messagebox.showwarning(
                        "Highlight Keywords",
                        "No valid highlight keywords were detected. Reverting to defaults.",
                    )
                candidate = ""
                parsed = dict(ENV_HIGHLIGHT_KEYWORDS)
        else:
            parsed = dict(ENV_HIGHLIGHT_KEYWORDS)
        if candidate:
            canonical = "; ".join(f"{keyword}:{parsed[keyword]}" for keyword in parsed)
            candidate = canonical
        else:
            candidate = ""
        if hasattr(self.app, "highlight_keywords_var"):
            self.app.highlight_keywords_var.set(candidate)
        self.app.settings["highlight_keywords"] = candidate
        apply_highlight_keywords(parsed)
        self.update_heatmap_button_state()
        if refresh_views:
            self.refresh_views_for_update()
            if show_feedback:
                if candidate:
                    self.app._log_status("Highlight keywords updated from settings.")
                else:
                    self.app._log_status("Highlight keywords reset to defaults.")
        if persist:
            self.app._save_settings()

    def apply_keywords_from_var(self, *, show_feedback: bool) -> None:
        value = (
            self.app.highlight_keywords_var.get()
            if hasattr(self.app, "highlight_keywords_var")
            else ""
        )
        self.update_keywords_setting(
            value,
            refresh_views=True,
            persist=True,
            show_feedback=show_feedback,
        )

    def on_return(self) -> None:
        self.apply_keywords_from_var(show_feedback=True)

    def on_apply_button(self) -> None:
        self.apply_keywords_from_var(show_feedback=True)
