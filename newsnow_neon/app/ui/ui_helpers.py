"""UI helper functions for AINewsApp.

Updates: v0.52 - 2025-11-18 - Extracted UI helpers (logging, status, filters, timezone, themes) to reduce application.py size.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser
import logging
from typing import Optional, Sequence, List
from datetime import datetime, timezone

from ..timeutils import coerce_timezone as _coerce_timezone_fn
from ..services import build_ticker_text
from ...summaries import configure_litellm_debug
from ..helpers.app_helpers import profile_name_options, derive_hover_color
from ...config import (
    COLOR_PROFILES,
    CUSTOM_PROFILE_NAME,
    DEFAULT_SETTINGS,
    DEFAULT_TIMEZONE,
    DEFAULT_COLOR_PROFILE_NAME,
    set_historical_cache_enabled,
)
from ...models import Headline, HeadlineTooltipData
from ...highlight import headline_highlight_color


# Logging helpers
def toggle_logs(app: tk.Tk) -> None:
    """Toggle logs panel visibility and persist setting."""
    if app.log_visible:
        app.log_frame.pack_forget()
        app.log_visible = False
        app.toggle_logs_btn.config(text="Show Logs")
    else:
        app.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        app.log_visible = True
        app.toggle_logs_btn.config(text="Hide Logs")
        flush_log_buffer(app)
    app.settings["log_visible"] = app.log_visible
    app._save_settings()


def append_log_line(app: tk.Tk, message: str) -> None:
    """Append a message to the log text widget, trimming old lines."""
    app.log_text.config(state="normal")
    app.log_text.insert(tk.END, message + "\n")
    line_count = int(app.log_text.index("end-1c").split(".")[0])
    if line_count > 500:
        app.log_text.delete("1.0", f"{line_count - 500}.0")
    app.log_text.see(tk.END)
    app.log_text.config(state="disabled")


def flush_log_buffer(app: tk.Tk) -> None:
    """Flush queued logs into the UI."""
    while app.log_buffer:
        _level, msg = app.log_buffer.popleft()
        append_log_line(app, msg)


def handle_log_record(app: tk.Tk, level: int, message: str) -> None:
    """Queue a log record and schedule a UI flush."""
    app.log_buffer.append((level, message))
    app.after(0, lambda: flush_log_buffer(app))


# Options/status helpers
def set_options_visibility(app: tk.Tk, visible: bool, *, persist: bool = True) -> None:
    """Show/hide the options container and update status summary."""
    app._options_visible = bool(visible)
    if visible:
        if not app.options_container.winfo_ismapped():
            app.options_container.pack(fill="x", padx=10, pady=(0, 10))
        app.options_toggle_btn.config(text="Hide Options")
    else:
        app.options_container.pack_forget()
        app.options_toggle_btn.config(text="Show Options")
    if persist:
        app.settings["options_visible"] = app._options_visible
        app._save_settings()
    update_status_summary(app)


def toggle_options_panel(app: tk.Tk) -> None:
    """Toggle the options panel visibility."""
    set_options_visibility(app, not app._options_visible)


def ensure_options_visible(app: tk.Tk) -> None:
    """Ensure options are visible without persisting the setting."""
    if not app._options_visible:
        set_options_visibility(app, True, persist=False)


def update_status_summary(app: tk.Tk) -> None:
    """Update compact status summary when options are hidden."""
    if not hasattr(app, "status_summary_label"):
        return
    if app._options_visible:
        if app.status_summary_label.winfo_ismapped():
            app.status_summary_label.pack_forget()
        app.status_summary_var.set("")
        return
    parts: List[str] = []
    if bool(app.background_watch_var.get()):
        parts.append(app.new_headlines_var.get())
    parts.append(app.last_refresh_var.get())
    if bool(app.auto_refresh_var.get()):
        parts.append(app.next_refresh_var.get())
    text = " | ".join(part for part in parts if part)
    if not text:
        text = "Options hidden"
    app.status_summary_var.set(text)
    if not app.status_summary_label.winfo_ismapped():
        app.status_summary_label.pack(side="right", padx=(10, 0))


# Filter helpers
def clear_search(app: tk.Tk, event: Optional[tk.Event] = None) -> Optional[str]:
    """Clear the search query and optionally consume the event."""
    if app.search_var.get():
        app.search_var.set("")
    if event is not None:
        return "break"
    return None


def on_search_change(app: tk.Tk, *_args: object) -> None:
    """Re-render list when search input changes."""
    if getattr(app, "_loading_settings", False):
        return
    app._render_filtered_headlines()


def on_section_filter_change(app: tk.Tk, *_args: object) -> None:
    """Re-render list when section filter changes."""
    if getattr(app, "_loading_settings", False):
        return
    if getattr(app, "_suppress_section_filter_callback", False):
        return
    app._render_filtered_headlines()


def matches_filters(app: tk.Tk, headline: Headline) -> bool:
    """Return True if the headline matches current search and section filters."""
    section_filter = (app.section_filter_var.get() or "").strip()
    if section_filter and section_filter != "All sections":
        section_value = (
            headline.section.strip()
            if isinstance(headline.section, str)
            else ""
        )
        if section_value != section_filter:
            return False

    query = (app.search_var.get() or "").strip().lower()
    if not query:
        return True

    tokens = [token for token in query.split() if token]
    if not tokens:
        return True

    haystack_parts = [
        headline.title,
        headline.source,
        headline.section,
        headline.published_time,
        headline.published_at,
        headline.url,
    ]
    haystack = " ".join(
        part.strip()
        for part in haystack_parts
        if isinstance(part, str) and part.strip()
    ).lower()

    return all(token in haystack for token in tokens)


def filtered_entries(app: tk.Tk) -> List[tuple[int, Headline]]:
    """Return (index, headline) pairs that match current filters."""
    results: List[tuple[int, Headline]] = []
    for index, headline in enumerate(app.headlines):
        if matches_filters(app, headline):
            results.append((index, headline))
    return results


def refresh_section_filter_menu(app: tk.Tk, headlines: Sequence) -> None:
    """Refresh section choices based on current headlines."""
    sections = {
        h.section.strip()
        for h in headlines
        if isinstance(h.section, str) and h.section.strip()
    }
    options = ["All sections", *sorted(sections)]
    if options == app._section_filter_options:
        return
    app._section_filter_options = options
    menu = app.section_filter_menu["menu"]
    menu.delete(0, "end")
    for option in options:
        menu.add_command(
            label=option,
            command=lambda value=option: app.section_filter_var.set(value),
        )
    if app.section_filter_var.get() not in options:
        app._suppress_section_filter_callback = True
        app.section_filter_var.set("All sections")
        app._suppress_section_filter_callback = False


# Timezone helpers
def refresh_timezone_menu(app: tk.Tk) -> None:
    """Refresh timezone choices while deduplicating options."""
    menu = app.timezone_menu["menu"]
    menu.delete(0, "end")
    seen: set[str] = set()
    deduped_options: List[str] = []
    for option in app._timezone_options:
        if option not in seen:
            seen.add(option)
            deduped_options.append(option)
    app._timezone_options = deduped_options
    for option in app._timezone_options:
        menu.add_command(
            label=option,
            command=lambda value=option: app.timezone_var.set(value),
        )


def on_timezone_change(app: tk.Tk, *_args: object) -> None:
    """Apply timezone selection, persisting if not loading from store."""
    if app._suppress_timezone_callback:
        return
    persist = not getattr(app, "_loading_settings", False)
    apply_timezone_selection(app, app.timezone_var.get(), persist=persist)


def apply_timezone_selection(app: tk.Tk, value: str, *, persist: bool) -> None:
    """Apply timezone and re-render headlines in the new zone."""
    normalized, zone = _coerce_timezone_fn(value)
    app._timezone_name = normalized
    app._timezone = zone
    if normalized not in app._timezone_options:
        app._timezone_options.append(normalized)
        refresh_timezone_menu(app)
    if app.timezone_var.get() != normalized:
        app._suppress_timezone_callback = True
        app.timezone_var.set(normalized)
        app._suppress_timezone_callback = False
    app.settings["timezone"] = normalized
    if persist and not getattr(app, "_loading_settings", False):
        app._save_settings()
    refresh_timezone_display(app)


def refresh_timezone_display(app: tk.Tk) -> None:
    """Re-render current headlines with updated timezone labeling."""
    if not app.headlines:
        return
    ticker_text = app._current_ticker_text or build_ticker_text(app.headlines)
    app._update_content(
        headlines=app.headlines,
        ticker_text=ticker_text,
        from_cache=app._last_headline_from_cache,
        reschedule=False,
        log_status=False,
    )


# Theme/color profile helpers
def apply_color_profile(app: tk.Tk, selected: Optional[str] = None) -> None:
    """Apply a named color profile to ticker widgets and persist setting."""
    name = selected or app.color_profile_var.get()
    if name not in COLOR_PROFILES:
        return
    profile = COLOR_PROFILES[name]
    app.ticker.apply_color_profile(profile)
    app.full_ticker.apply_color_profile(profile)
    if hasattr(app, "ticker_bg_var"):
        app.ticker_bg_var.set(profile["background"])
        app.ticker_fg_var.set(profile["text"])
    app.settings["color_profile"] = name
    app._save_settings()


def choose_color(app: tk.Tk, target: str) -> None:
    """Choose a custom color and update ticker colors."""
    initial = app.ticker_bg_var.get() if target == "background" else app.ticker_fg_var.get()
    color = colorchooser.askcolor(initialcolor=initial)[1]
    if not color:
        return
    if target == "background":
        app.ticker_bg_var.set(color)
    else:
        app.ticker_fg_var.set(color)
    update_ticker_colors(app)
    app.color_profile_var.set(CUSTOM_PROFILE_NAME)


def update_ticker_colors(app: tk.Tk) -> None:
    """Apply custom ticker colors and persist a derived profile."""
    background = app.ticker_bg_var.get()
    text = app.ticker_fg_var.get()
    app.ticker.set_colors(background=background, text=text)
    hover_color = app.ticker.hover_color
    COLOR_PROFILES[CUSTOM_PROFILE_NAME] = {
        "background": background,
        "text": text,
        "hover": hover_color,
    }
    app.settings["custom_background"] = background
    app.settings["custom_text"] = text
    app.settings["color_profile"] = CUSTOM_PROFILE_NAME
    if not getattr(app, "_loading_settings", False):
        app.color_profile_var.set(CUSTOM_PROFILE_NAME)
    refresh_profile_menu(app)
    app._save_settings()


def refresh_profile_menu(app: tk.Tk) -> None:
    """Refresh color profile menu options."""
    options = profile_name_options()
    menu = app.profile_menu["menu"]
    menu.delete(0, "end")
    for name in options:
        menu.add_command(
            label=name,
            command=lambda value=name: on_profile_selected(app, value),
        )


def on_profile_selected(app: tk.Tk, name: str) -> None:
    """Apply a selected color profile from the menu."""
    app.color_profile_var.set(name)
    apply_color_profile(app, name)


def refresh_color_profiles(app: tk.Tk) -> None:
    """Expose profile menu refresh for future dynamic additions."""
    refresh_profile_menu(app)


def refresh_relative_age_labels(app: tk.Tk) -> None:
    """Refresh relative age labels for listbox rows and reschedule."""
    if not app._listbox_line_to_headline:
        return

    now_utc = datetime.now(timezone.utc)
    updated_any = False

    for line, original_idx in list(app._listbox_line_to_headline.items()):
        if original_idx < 0 or original_idx >= len(app.headlines):
            continue

        headline = app.headlines[original_idx]
        localized = app._headline_with_timezone(headline)
        age_minutes = app._headline_age_minutes(headline, now_utc)
        relative_label = app._format_relative_age(age_minutes)

        context = app._listbox_line_details.get(line)
        display_index = (
            context.display_index
            if context and context.display_index is not None
            else original_idx + 1
        )

        row_color = headline_highlight_color(localized)
        metadata_parts = app._compose_metadata_parts(localized, relative_label)
        metadata_text = " • ".join(metadata_parts)
        metadata_with_dash = f" — {metadata_text}"

        prefix_len = app._listbox_line_prefix.get(line, 0)
        insert_index = f"{line}.0 + {prefix_len}c"
        line_end = f"{line}.end"

        app.listbox.configure(state="normal")
        app.listbox.delete(insert_index, line_end)

        row_tag = app._line_to_row_tag.get(line)
        metadata_tags: tuple[str, ...]
        if row_tag:
            metadata_tags = ("metadata", row_tag)
        else:
            metadata_tags = ("metadata",)

        app.listbox.insert(insert_index, metadata_with_dash, metadata_tags)

        color_tag = app.list_renderer.ensure_color_tag(
            row_color or app.listbox_default_fg
        )
        prefix_start = f"{line}.0"
        prefix_end = f"{line}.0 + {prefix_len}c"
        for tag in app._listbox_color_tags.values():
            app.listbox.tag_remove(tag, prefix_start, prefix_end)
        app.listbox.tag_add(color_tag, prefix_start, prefix_end)

        app.listbox.configure(state="disabled")
        app._listbox_line_metadata[line] = metadata_with_dash
        app._listbox_line_details[line] = HeadlineTooltipData(
            headline=localized,
            relative_age=relative_label,
            display_index=display_index,
            row_kind="title",
        )
        updated_any = True

    if updated_any:
        app._schedule_relative_age_refresh()


# Listbox helpers (moved from application controller to slim it)
def clear_headline_list(app: tk.Tk) -> None:
    """Clear the headline listbox and associated selection/tooltip state."""
    app.listbox.configure(state="normal")
    app.listbox.delete("1.0", tk.END)
    app.listbox.configure(state="disabled")
    app._listbox_line_to_headline.clear()
    app._listbox_line_details.clear()
    app._listbox_line_prefix.clear()
    app._listbox_line_metadata.clear()
    app._row_tag_to_line.clear()
    app._row_tag_to_headline.clear()
    app._line_to_row_tag.clear()
    app._listbox_hover_line = None
    app._listbox_last_tooltip_text = None
    app._selected_line = None
    clear_listbox_selection(app)
    if hasattr(app, "_listbox_tooltip"):
        app._listbox_tooltip.hide()
    # Refresh action buttons for current selection state.
    if hasattr(app, "_refresh_mute_button_state"):
        app._refresh_mute_button_state()


def clear_listbox_selection(app: tk.Tk) -> None:
    """Remove selection tag and reset selected line."""
    app.listbox.configure(state="normal")
    app.listbox.tag_remove("selected", "1.0", tk.END)
    app.listbox.configure(state="disabled")
    app._selected_line = None


def select_listbox_line(app: tk.Tk, line: int) -> None:
    """Select a specific line in the listbox, guarding bounds."""
    line_count = int(float(app.listbox.index("end-1c").split(".")[0]))
    if line < 1 or line > line_count:
        return
    app.listbox.configure(state="normal")
    app.listbox.tag_remove("selected", "1.0", tk.END)
    app.listbox.tag_add("selected", f"{line}.0", f"{line}.end")
    app.listbox.tag_raise("selected")
    app.listbox.configure(state="disabled")
    app._selected_line = line


def update_handler_level(app: tk.Tk) -> None:
    """Update log handler levels based on debug toggle."""
    if bool(app.debug_var.get()):
        app.log_handler.setLevel(logging.DEBUG)
        if hasattr(app, "console_handler"):
            app.console_handler.setLevel(logging.DEBUG)
        logging.getLogger(__name__).info("Debug logging enabled.")
    else:
        app.log_handler.setLevel(logging.INFO)
        if hasattr(app, "console_handler"):
            app.console_handler.setLevel(logging.INFO)
        logging.getLogger(__name__).info(
            "Debug logging disabled; showing INFO and above."
        )


def apply_settings_from_store(app: tk.Tk) -> None:
    """Apply persisted settings to the UI and controllers."""
    # Highlight keywords
    highlight_value = app.settings.get("highlight_keywords", "")
    if not isinstance(highlight_value, str):
        highlight_value = ""
    app._update_highlight_keywords_setting(
        highlight_value,
        refresh_views=True,
        persist=False,
        show_feedback=False,
    )

    # Ticker speed
    speed = int(app.settings.get("ticker_speed", DEFAULT_SETTINGS["ticker_speed"]))
    app.ticker_speed_var.set(speed)
    app.ticker.set_speed(speed)
    app.settings["ticker_speed"] = speed

    # Timezone selection
    timezone_value = str(app.settings.get("timezone", DEFAULT_TIMEZONE))
    apply_timezone_selection(app, timezone_value, persist=False)

    # Color profile
    profile = app.settings.get("color_profile", DEFAULT_SETTINGS["color_profile"])
    if profile == CUSTOM_PROFILE_NAME:
        background = app.settings.get(
            "custom_background", DEFAULT_SETTINGS["custom_background"]
        )
        text_color = app.settings.get("custom_text", DEFAULT_SETTINGS["custom_text"])
        COLOR_PROFILES[CUSTOM_PROFILE_NAME] = {
            "background": background,
            "text": text_color,
            "hover": derive_hover_color(text_color),
        }
        app.color_profile_var.set(CUSTOM_PROFILE_NAME)
        app.ticker_bg_var.set(background)
        app.ticker_fg_var.set(text_color)
        app.ticker.set_colors(background=background, text=text_color)
    elif profile in COLOR_PROFILES:
        app.color_profile_var.set(profile)
        apply_color_profile(app, profile)
        profile_colors = COLOR_PROFILES[profile]
        app.ticker_bg_var.set(profile_colors["background"])
        app.ticker_fg_var.set(profile_colors["text"])
    else:
        app.color_profile_var.set(DEFAULT_COLOR_PROFILE_NAME)
        apply_color_profile(app, DEFAULT_COLOR_PROFILE_NAME)
        profile_colors = COLOR_PROFILES[DEFAULT_COLOR_PROFILE_NAME]
        app.ticker_bg_var.set(profile_colors["background"])
        app.ticker_fg_var.set(profile_colors["text"])

    # Logs visibility
    desired_log = bool(app.settings.get("log_visible", DEFAULT_SETTINGS["log_visible"]))
    if desired_log and not app.log_visible:
        app.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        app.log_visible = True
        app.toggle_logs_btn.config(text="Hide Logs")
        flush_log_buffer(app)
    elif not desired_log and app.log_visible:
        app.log_frame.pack_forget()
        app.log_visible = False
        app.toggle_logs_btn.config(text="Show Logs")

    # Debug/logging levels
    debug_enabled = bool(app.settings.get("debug_mode", DEFAULT_SETTINGS["debug_mode"]))
    app.debug_var.set(debug_enabled)
    update_handler_level(app)

    # LiteLLM debug toggle
    litellm_debug_enabled = bool(
        app.settings.get("litellm_debug", DEFAULT_SETTINGS["litellm_debug"])
    )
    app.litellm_debug_var.set(litellm_debug_enabled)
    configure_litellm_debug(litellm_debug_enabled)
    app.settings["litellm_debug"] = litellm_debug_enabled

    # Historical cache
    historical_enabled = bool(
        app.settings.get(
            "historical_cache_enabled",
            DEFAULT_SETTINGS["historical_cache_enabled"],
        )
    )
    app.historical_cache_var.set(historical_enabled)
    app.settings["historical_cache_enabled"] = historical_enabled
    set_historical_cache_enabled(historical_enabled)

    # Auto refresh
    auto_enabled = bool(
        app.settings.get(
            "auto_refresh_enabled", DEFAULT_SETTINGS["auto_refresh_enabled"]
        )
    )
    minutes = max(
        1,
        int(
            app.settings.get(
                "auto_refresh_minutes",
                DEFAULT_SETTINGS["auto_refresh_minutes"],
            )
        ),
    )
    app.auto_refresh_var.set(auto_enabled)
    app.auto_refresh_minutes_var.set(minutes)
    app.settings["auto_refresh_enabled"] = auto_enabled
    app.settings["auto_refresh_minutes"] = minutes

    # Background watch
    background_watch_enabled = bool(
        app.settings.get(
            "background_watch_enabled",
            DEFAULT_SETTINGS["background_watch_enabled"],
        )
    )
    app.background_watch_var.set(background_watch_enabled)
    app.settings["background_watch_enabled"] = background_watch_enabled

    threshold = app.background_watch_controller.coerce_threshold(
        app.settings.get(
            "background_watch_refresh_threshold",
            DEFAULT_SETTINGS["background_watch_refresh_threshold"],
        )
    )
    app._background_refresh_threshold = threshold
    app.background_watch_threshold_var.set(threshold)
    app.settings["background_watch_refresh_threshold"] = threshold
    if not background_watch_enabled:
        app._pending_new_headlines = 0
        app._last_reported_pending = 0
    app.background_watch_controller.update_label()
    app._schedule_background_watch(immediate=background_watch_enabled)

    # Persist and refresh UI menus/panels
    app.settings["color_profile"] = app.color_profile_var.get()
    app.settings["log_visible"] = app.log_visible
    refresh_profile_menu(app)
    set_options_visibility(
        app,
        bool(app.settings.get("options_visible", app._options_visible)),
        persist=False,
    )
    app._refresh_history_controls_state()
    update_status_summary(app)


__all__ = [
    "toggle_logs",
    "append_log_line",
    "flush_log_buffer",
    "handle_log_record",
    "set_options_visibility",
    "toggle_options_panel",
    "ensure_options_visible",
    "update_status_summary",
    "clear_search",
    "on_search_change",
    "on_section_filter_change",
    "refresh_section_filter_menu",
    "refresh_timezone_menu",
    "on_timezone_change",
    "apply_timezone_selection",
    "refresh_timezone_display",
    "apply_color_profile",
    "choose_color",
    "update_ticker_colors",
    "refresh_profile_menu",
    "on_profile_selected",
    "refresh_color_profiles",
    "refresh_relative_age_labels",
    "clear_headline_list",
    "clear_listbox_selection",
    "select_listbox_line",
    "apply_settings_from_store",
    "update_handler_level",
]