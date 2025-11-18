"""Tkinter application controller for NewsNow Neon.

Updates: v0.50 - 2025-01-07 - Moved AINewsApp controller and helpers from the legacy script and introduced service injection.
Updates: v0.51 - 2025-10-29 - Wired application metadata import after relocating legacy launcher.
Updates: v0.52 - 2025-11-18 - Added one-click mute source/keyword actions and UI wiring.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import tkinter as tk
from collections import deque
from datetime import datetime, timedelta, timezone, tzinfo
from dataclasses import replace
from tkinter import colorchooser, font, messagebox
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
import threading
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import webbrowser
from urllib.parse import urlparse

from .config import (
    COLOR_PROFILES,
    CUSTOM_PROFILE_NAME,
    DEFAULT_COLOR_PROFILE,
    DEFAULT_COLOR_PROFILE_NAME,
    DEFAULT_SETTINGS,
    DEFAULT_TIMEZONE,
    TIMEZONE_CHOICES,
    SECTIONS,
    REDIS_URL,
    CACHE_KEY,
    BACKGROUND_WATCH_INTERVAL_MS,
    BACKGROUND_WATCH_INITIAL_DELAY_MS,
    SETTINGS_PATH,
    set_historical_cache_enabled,
    fixed_zone_fallback,
)
from .highlight import (
    ENV_HIGHLIGHT_KEYWORDS,
    apply_highlight_keywords,
    compose_headline_tooltip,
    has_highlight_pattern,
    headline_highlight_color,
    parse_highlight_keywords,
)
from .models import (
    Headline,
    HeadlineTooltipData,
    HistoricalSnapshot,
    HoverTooltip,
    LiveFlowState,
    RedisStatistics,
    TkQueueHandler,
)
from .cache import get_redis_client
from .settings_store import load_settings, save_settings
from .summaries import configure_litellm_debug
from .ui import AppInfoWindow, KeywordHeatmapWindow, NewsTicker, RedisStatsWindow, SummaryWindow
from .utils import parse_iso8601_utc as _parse_iso8601_utc
from .main import APP_METADATA

logger = logging.getLogger(__name__)

_SENSITIVE_ENV_PATTERN = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|API_KEY)$", re.IGNORECASE)

# Common stopwords ignored when auto-deriving a mute keyword from a title.
_MUTE_STOPWORDS: Set[str] = {
    "the",
    "and",
    "for",
    "with",
    "into",
    "from",
    "about",
    "this",
    "that",
    "will",
    "have",
    "has",
    "are",
    "was",
    "were",
    "to",
    "of",
    "in",
    "on",
    "by",
    "as",
    "at",
    "new",
    "breaking",
}

from .app.services import (
    configure_app_services,
    fetch_headlines,
    build_ticker_text,
    resolve_article_summary,
    persist_headlines_with_ticker,
    collect_redis_statistics,
    clear_cached_headlines,
    load_historical_snapshots,
)

# Modularized helpers
from .app.filtering import (
    filter_headlines as _filter_headlines_fn,
    normalise_exclusion_terms as _normalise_exclusion_terms_fn,
    split_exclusion_string as _split_exclusion_string_fn,
)
from .app.timeutils import (
    coerce_timezone as _coerce_timezone_fn,
    format_localized_timestamp as _format_localized_timestamp_fn,
)
from .app.rendering import (
    group_headlines_by_age as _group_headlines_by_age_fn,
    headline_age_minutes as _headline_age_minutes_fn,
    resolve_age_bucket as _resolve_age_bucket_fn,
    format_relative_age as _format_relative_age_fn,
    compose_metadata_parts as _compose_metadata_parts_fn,
)
from .app.actions import (
    extract_keyword_for_mute as _extract_keyword_for_mute_fn,
    derive_source_term as _derive_source_term_fn,
)


def _coerce_timezone(name: Optional[str]) -> tuple[str, tzinfo]:
    """Delegate to modular timeutils.coerce_timezone."""
    normalized, zone = _coerce_timezone_fn(name)
    return normalized, zone


def _format_localized_timestamp(timestamp: datetime, zone: tzinfo) -> tuple[str, str]:
    """Delegate to modular timeutils.format_localized_timestamp."""
    return _format_localized_timestamp_fn(timestamp, zone)


def _profile_name_options() -> List[str]:
    names = list(COLOR_PROFILES.keys())
    if CUSTOM_PROFILE_NAME not in COLOR_PROFILES:
        names.append(CUSTOM_PROFILE_NAME)
    else:
        names = [n for n in names if n != CUSTOM_PROFILE_NAME] + [CUSTOM_PROFILE_NAME]
    return names


def _derive_hover_color(hex_color: str, factor: float = 0.25) -> str:
    if not isinstance(hex_color, str) or not hex_color.startswith("#"):
        return hex_color

    hex_value = hex_color.lstrip("#")
    if len(hex_value) == 3:
        hex_value = ''.join(ch * 2 for ch in hex_value)
    if len(hex_value) != 6:
        return hex_color

    try:
        r = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        b = int(hex_value[4:6], 16)
    except ValueError:
        return hex_color

    def _mix(component: int) -> int:
        return min(255, int(component + (255 - component) * factor))

    return "#{:02X}{:02X}{:02X}".format(_mix(r), _mix(g), _mix(b))



class AINewsApp(tk.Tk):
    """Tkinter app that displays AI headlines and a scrolling ticker."""

    def __init__(self, refresh_interval_ms: int = 900_000) -> None:
        super().__init__()
        self.title("AI Headlines")
        self.geometry(DEFAULT_SETTINGS["window_geometry"])
        self.configure(bg="black")

        self.refresh_interval = refresh_interval_ms
        self.headlines: List[Headline] = []
        self._latest_status: str = ""
        self.log_buffer: deque[tuple[int, str]] = deque()
        self._refresh_job: Optional[str] = None
        self._last_refresh_time: Optional[datetime] = None
        self._next_refresh_time: Optional[datetime] = None
        self._countdown_job: Optional[str] = None
        self._relative_age_job: Optional[str] = None
        self._background_watch_job: Optional[str] = None
        self._background_watch_running = False
        self._pending_new_headlines = 0
        self._last_reported_pending = 0
        self._background_candidate_keys: Set[tuple[str, str]] = set()
        self._background_watch_next_run: Optional[datetime] = None
        self._last_geometry: Optional[str] = None
        self._geometry_tracking_ready = False
        self._current_ticker_text = "No headlines available right now."
        self._suppress_timezone_callback = False
        self._last_headline_from_cache = False
        self._listbox_line_to_headline: Dict[int, int] = {}
        self._listbox_line_details: Dict[int, HeadlineTooltipData] = {}
        self._listbox_line_prefix: Dict[int, int] = {}
        self._listbox_line_metadata: Dict[int, str] = {}
        self._row_tag_to_line: Dict[str, int] = {}
        self._row_tag_to_headline: Dict[str, int] = {}
        self._line_to_row_tag: Dict[int, str] = {}
        self._listbox_hover_line: Optional[int] = None
        self._listbox_last_tooltip_text: Optional[str] = None
        self._selected_line: Optional[int] = None
        self._heatmap_window: Optional[KeywordHeatmapWindow] = None
        self._info_window: Optional[AppInfoWindow] = None
        self._redis_stats_window: Optional[RedisStatsWindow] = None
        self._loading_redis_stats = False
        self._raw_headlines: List[Headline] = []
        self._raw_total_headlines = 0
        self._last_excluded_count = 0
        self._base_total_headlines = 0
        self._base_source_label = "live"
        self._base_summary_text = "No headlines available right now."
        self._history_mode = False
        self._history_entries: List[HistoricalSnapshot] = []
        self._history_active_snapshot: Optional[HistoricalSnapshot] = None
        self._loading_history = False
        self._last_live_payload: Optional[tuple[List[Headline], str, bool]] = None
        self._last_live_flow_state: Optional[LiveFlowState] = None
        self._live_ticker_items: List[Headline] = []
        self._live_full_ticker_items: List[Headline] = []

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Configure>", self._on_root_configure)

        self.log_handler = TkQueueHandler(self._handle_log_record)
        self.log_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
            )
        )
        self.log_handler.setLevel(logging.INFO)
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(logging.DEBUG)
        for handler in list(self.root_logger.handlers):
            if isinstance(handler, TkQueueHandler):
                self.root_logger.removeHandler(handler)
        self.root_logger.addHandler(self.log_handler)
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
            )
        )
        self.console_handler.setLevel(logging.INFO)
        self.root_logger.addHandler(self.console_handler)

        self.settings = load_settings()
        stored_highlights = self.settings.get("highlight_keywords", "")
        if not isinstance(stored_highlights, str):
            stored_highlights = ""
        self.highlight_keywords_var = tk.StringVar(value=stored_highlights)
        self._update_highlight_keywords_setting(
            stored_highlights,
            refresh_views=False,
            persist=False,
            show_feedback=False,
        )
        initial_timezone_value = str(
            self.settings.get("timezone", DEFAULT_TIMEZONE)
        )
        self._timezone_name, self._timezone = _coerce_timezone(initial_timezone_value)
        if self._timezone_name != initial_timezone_value:
            self.settings["timezone"] = self._timezone_name
        self._timezone_options: List[str] = list(TIMEZONE_CHOICES)
        if self._timezone_name not in self._timezone_options:
            self._timezone_options.insert(0, self._timezone_name)

        exclusions_list, exclusions_set = self._normalise_exclusion_terms(
            self.settings.get("headline_exclusions")
        )
        self.settings["headline_exclusions"] = exclusions_list
        self._exclusion_terms: Set[str] = exclusions_set
        self.exclude_terms_var = tk.StringVar(value=", ".join(exclusions_list))

        stored_geometry = self.settings.get("window_geometry")
        if isinstance(stored_geometry, str) and stored_geometry.strip():
            try:
                self.geometry(stored_geometry)
                self._last_geometry = stored_geometry
            except tk.TclError:
                logger.debug("Ignoring invalid stored geometry value: %s", stored_geometry)
        self.debug_var = tk.BooleanVar(
            value=bool(self.settings.get("debug_mode", DEFAULT_SETTINGS["debug_mode"]))
        )
        self.litellm_debug_var = tk.BooleanVar(
            value=bool(
                self.settings.get("litellm_debug", DEFAULT_SETTINGS["litellm_debug"])
            )
        )
        self.historical_cache_var = tk.BooleanVar(
            value=bool(
                self.settings.get(
                    "historical_cache_enabled",
                    DEFAULT_SETTINGS["historical_cache_enabled"],
                )
            )
        )
        self.auto_refresh_var = tk.BooleanVar(
            value=bool(
                self.settings.get(
                    "auto_refresh_enabled", DEFAULT_SETTINGS["auto_refresh_enabled"]
                )
            )
        )
        self.background_watch_var = tk.BooleanVar(
            value=bool(
                self.settings.get(
                    "background_watch_enabled",
                    DEFAULT_SETTINGS["background_watch_enabled"],
                )
            )
        )
        threshold_value = self.settings.get(
            "background_watch_refresh_threshold",
            DEFAULT_SETTINGS["background_watch_refresh_threshold"],
        )
        self._background_refresh_threshold = self._coerce_background_watch_threshold(
            threshold_value
        )
        self.settings["background_watch_refresh_threshold"] = self._background_refresh_threshold
        self.background_watch_threshold_var = tk.IntVar(
            value=self._background_refresh_threshold
        )
        self.new_headlines_var = tk.StringVar(value="Background watch: off")
        self.auto_refresh_minutes_var = tk.IntVar(
            value=int(
                self.settings.get(
                    "auto_refresh_minutes", DEFAULT_SETTINGS["auto_refresh_minutes"]
                )
            )
        )
        self._options_visible = bool(self.settings.get("options_visible", False))
        COLOR_PROFILES[CUSTOM_PROFILE_NAME] = {
            "background": self.settings.get(
                "custom_background", DEFAULT_SETTINGS["custom_background"]
            ),
            "text": self.settings.get("custom_text", DEFAULT_SETTINGS["custom_text"]),
            "hover": _derive_hover_color(
                self.settings.get("custom_text", DEFAULT_SETTINGS["custom_text"])
            ),
        }
        self._loading_settings = True
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        self.section_filter_var = tk.StringVar(value="All sections")
        self.section_filter_var.trace_add("write", self._on_section_filter_change)
        initial_sections = sorted({section.label for section in SECTIONS})
        self._section_filter_options: List[str] = ["All sections", *initial_sections]
        self._suppress_section_filter_callback = False

        self.ticker = NewsTicker(self, name="neon1")
        self.ticker.pack(fill="x", padx=10, pady=(10, 5))

        self.full_ticker = NewsTicker(
            self,
            speed=1,
            max_title_length=None,
            font_spec=("Consolas", 14, "bold"),
            item_spacing=120,
            name="neon2",
        )
        self.full_ticker.pack(fill="x", padx=10, pady=(0, 10))

        search_frame = tk.Frame(self, bg="black")
        search_frame.pack(fill="x", padx=10, pady=(0, 5))

        search_label = tk.Label(search_frame, text="Search:", bg="black", fg="lightgray")
        search_label.pack(side="left")

        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=32,
            highlightthickness=0,
        )
        self.search_entry.pack(side="left", padx=(6, 6))
        self.search_entry.bind("<Escape>", self._clear_search)

        clear_button = tk.Button(search_frame, text="Clear", command=self._clear_search)
        clear_button.pack(side="left")

        filter_label = tk.Label(search_frame, text="Section:", bg="black", fg="lightgray")
        filter_label.pack(side="left", padx=(12, 4))

        self.section_filter_menu = tk.OptionMenu(
            search_frame,
            self.section_filter_var,
            *self._section_filter_options,
        )
        self.section_filter_menu.configure(bg="#2f2f2f", fg="white", highlightthickness=0)
        self.section_filter_menu["menu"].configure(bg="#2f2f2f", fg="white")
        self.section_filter_menu.pack(side="left")

        exclude_label = tk.Label(
            search_frame,
            text="Exclude terms:",
            bg="black",
            fg="lightgray",
        )
        exclude_label.pack(side="left", padx=(12, 4))

        self.exclude_entry = tk.Entry(
            search_frame,
            textvariable=self.exclude_terms_var,
            width=40,
            highlightthickness=0,
        )
        self.exclude_entry.pack(side="left", padx=(6, 6))
        self.exclude_entry.bind("<Return>", self._apply_exclusion_terms)
        self.exclude_entry.bind("<FocusOut>", self._apply_exclusion_terms)

        apply_exclude_btn = tk.Button(
            search_frame,
            text="Apply",
            command=self._apply_exclusion_terms,
        )
        apply_exclude_btn.pack(side="left")

        clear_exclude_btn = tk.Button(
            search_frame,
            text="Clear",
            command=self._clear_exclusion_terms,
        )
        clear_exclude_btn.pack(side="left", padx=(6, 0))

        list_frame = tk.Frame(self, name="list", bg="black")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        default_font = font.nametofont("TkDefaultFont")
        base_family = default_font.actual("family") or "Segoe UI"
        base_size = max(int(default_font.actual("size")), 12)
        base_weight = default_font.actual("weight") or "normal"
        self._listbox_title_font = font.Font(
            family=base_family,
            size=base_size,
            weight=base_weight,
        )
        self._listbox_metadata_font = font.Font(
            family=base_family,
            size=max(base_size - 2, 8),
            weight=base_weight,
            slant="italic",
        )
        self._listbox_group_font = font.Font(
            family=base_family,
            size=base_size,
            weight="bold",
        )
        self.listbox_default_fg = "#FFFFFF"
        self._listbox_metadata_fg = "#B0B0B0"

        self.listbox = tk.Text(
            list_frame,
            wrap="none",
            bg="#101010",
            fg=self.listbox_default_fg,
            insertbackground="white",
            height=0,
            state="disabled",
            relief="flat",
        )
        self.listbox.pack(fill="both", expand=True)
        self.listbox.configure(yscrollcommand=scrollbar.set, cursor="arrow")
        scrollbar.config(command=self.listbox.yview)
        self.listbox.tag_configure("group", font=self._listbox_group_font, foreground="#89CFF0")
        self.listbox.tag_configure("title", font=self._listbox_title_font, foreground=self.listbox_default_fg)
        self.listbox.tag_configure("metadata", font=self._listbox_metadata_font, foreground=self._listbox_metadata_fg)
        self.listbox.tag_configure("message", font=self._listbox_title_font, foreground=self.listbox_default_fg)
        self.listbox.tag_configure("selected", background="#264653")
        self.listbox.tag_raise("selected")

        self._listbox_color_tags: Dict[str, str] = {}
        self._listbox_tooltip = HoverTooltip(self.listbox, wraplength=520)
        self.listbox.bind("<Button-1>", self._on_listbox_click)
        self.listbox.bind("<Double-Button-1>", self.open_selected_headline)
        self.listbox.bind("<Return>", self.open_selected_headline)
        self.listbox.bind("<Up>", lambda event: self._on_listbox_nav(-1))
        self.listbox.bind("<Down>", lambda event: self._on_listbox_nav(1))
        self.listbox.bind("<Motion>", self._on_listbox_motion)
        self.listbox.bind("<Leave>", self._on_listbox_leave)
        self.listbox.bind("<Key>", lambda _event: "break")

        action_bar = tk.Frame(self, bg="black")
        action_bar.pack(fill="x", padx=10, pady=(0, 10))
        self.action_bar = action_bar

        self.options_toggle_btn = tk.Button(
            action_bar,
            text="Show Options",
            command=self._toggle_options_panel,
        )
        self.options_toggle_btn.pack(side="left")

        self.action_refresh_btn = tk.Button(
            action_bar,
            text="Refresh",
            command=lambda: self.refresh_headlines(force_refresh=True),
        )
        self.action_refresh_btn.pack(side="left", padx=(10, 0))

        right_action_cluster = tk.Frame(action_bar, bg="black")
        right_action_cluster.pack(side="right")

        self.status_summary_var = tk.StringVar(value="")
        self.status_summary_label = tk.Label(
            right_action_cluster,
            textvariable=self.status_summary_var,
            bg="black",
            fg="#89CFF0",
            font=("Segoe UI", 10, "italic"),
        )
        self.status_summary_label.pack(side="right", padx=(10, 0))
        self.status_summary_label.pack_forget()

        self.exit_btn = tk.Button(
            right_action_cluster, text="Exit", command=self._on_close
        )
        self.exit_btn.pack(side="right", padx=(10, 0))

        self.info_btn = tk.Button(
            right_action_cluster, text="Info", command=self._show_info_window
        )
        self.info_btn.pack(side="right", padx=(10, 0))

        # One-click mute actions for selected headline.
        self.mute_keyword_btn = tk.Button(
            right_action_cluster,
            text="Mute Keyword",
            command=self._mute_selected_keyword,
            state=tk.DISABLED,
        )
        self.mute_keyword_btn.pack(side="right", padx=(10, 0))

        self.mute_source_btn = tk.Button(
            right_action_cluster,
            text="Mute Source",
            command=self._mute_selected_source,
            state=tk.DISABLED,
        )
        self.mute_source_btn.pack(side="right", padx=(10, 0))

        self.options_container = tk.Frame(self, bg="black")
        self.options_container.pack(fill="x", padx=10, pady=(0, 10))

        controls = tk.Frame(self.options_container, bg="black")
        controls.pack(fill="x", pady=(0, 10))

        refresh_btn = tk.Button(
            controls,
            text="Refresh Headlines",
            command=lambda: self.refresh_headlines(force_refresh=True),
        )
        refresh_btn.pack(side="left")

        self.clear_cache_btn = tk.Button(
            controls, text="Clear Cache", command=self.clear_cache
        )
        self.clear_cache_btn.pack(side="left", padx=10)

        self.redis_stats_btn = tk.Button(
            controls,
            text="Redis Stats",
            command=self._open_redis_stats,
            state=tk.NORMAL if REDIS_URL else tk.DISABLED,
        )
        self.redis_stats_btn.pack(side="left", padx=10)

        heatmap_state = tk.NORMAL if has_highlight_pattern() else tk.DISABLED
        self.heatmap_btn = tk.Button(
            controls,
            text="Keyword Heatmap",
            command=self.open_heatmap,
            state=heatmap_state,
        )
        self.heatmap_btn.pack(side="left", padx=10)
        self._update_heatmap_button_state()

        self.toggle_logs_btn = tk.Button(
            controls, text="Show Logs", command=self._toggle_logs
        )
        self.toggle_logs_btn.pack(side="left", padx=10)

        self.redis_meter_var = tk.StringVar(value="Redis: checking…")
        self.redis_meter_label = tk.Label(
            controls,
            textvariable=self.redis_meter_var,
            bg="black",
            fg="#FFB347",
            anchor="w",
        )
        self.redis_meter_label.pack(side="left", padx=10)

        highlight_frame = tk.Frame(self.options_container, bg="black")
        highlight_frame.pack(fill="x", pady=(0, 10))

        highlight_label = tk.Label(
            highlight_frame,
            text="Highlight keywords:",
            bg="black",
            fg="lightgray",
        )
        highlight_label.pack(side="left")

        self.highlight_entry = tk.Entry(
            highlight_frame,
            textvariable=self.highlight_keywords_var,
            width=60,
            highlightthickness=0,
        )
        self.highlight_entry.pack(side="left", padx=(10, 6), fill="x", expand=True)
        self.highlight_entry.bind("<Return>", self._on_highlight_keywords_return)

        highlight_apply_btn = tk.Button(
            highlight_frame,
            text="Apply",
            command=self._on_highlight_keywords_button,
        )
        highlight_apply_btn.pack(side="left")

        highlight_hint = tk.Label(
            self.options_container,
            text="Format: keyword:#HEX; term2:#HEX (leave blank to use defaults or NEWS_HIGHLIGHT_KEYWORDS).",
            bg="black",
            fg="#888888",
            font=("Segoe UI", 9, "italic"),
            justify="left",
            wraplength=760,
        )
        highlight_hint.pack(fill="x", padx=4, pady=(0, 5))

        history_controls = tk.Frame(self.options_container, bg="black")
        history_controls.pack(fill="x", pady=(0, 5))

        history_label = tk.Label(
            history_controls,
            text="History (last 24h):",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10, "bold"),
        )
        history_label.pack(side="left")

        self.history_status_var = tk.StringVar(
            value="History mode off — refresh to browse cached snapshots."
        )
        history_status_label = tk.Label(
            history_controls,
            textvariable=self.history_status_var,
            bg="black",
            fg="#89CFF0",
            font=("Segoe UI", 10, "italic"),
        )
        history_status_label.pack(side="left", padx=(10, 0))

        self.exit_history_btn = tk.Button(
            history_controls,
            text="Return to Live",
            command=self._exit_history_mode,
            state=tk.DISABLED,
        )
        self.exit_history_btn.pack(side="right")

        self.history_reload_btn = tk.Button(
            history_controls,
            text="Refresh History",
            command=self._request_history_refresh,
            state=tk.NORMAL if REDIS_URL else tk.DISABLED,
        )
        self.history_reload_btn.pack(side="right", padx=(0, 10))

        history_list_frame = tk.Frame(self.options_container, bg="black")
        history_list_frame.pack(fill="x", pady=(0, 10))

        history_scrollbar = tk.Scrollbar(history_list_frame)
        history_scrollbar.pack(side="right", fill="y")

        self.history_listbox = tk.Listbox(
            history_list_frame,
            height=6,
            font=("Segoe UI", 11),
            activestyle="none",
            bg="#101010",
            fg="white",
            selectbackground="#3A506B",
            selectforeground="white",
            yscrollcommand=history_scrollbar.set,
        )
        self.history_listbox.pack(fill="both", expand=False)
        history_scrollbar.config(command=self.history_listbox.yview)
        self.history_listbox.insert(
            tk.END,
            "History snapshots appear here when Redis history caching is enabled.",
        )
        self.history_listbox.configure(state=tk.DISABLED)
        self.history_listbox.bind("<<ListboxSelect>>", self._on_history_select)
        self.history_listbox.bind("<Double-Button-1>", self._activate_history_selection)
        self.history_listbox.bind("<Return>", self._activate_history_selection)
        self.history_listbox_hover = HoverTooltip(self.history_listbox, wraplength=360)
        self.history_listbox.bind("<Motion>", self._on_history_motion)
        self.history_listbox.bind("<Leave>", lambda _event: self.history_listbox_hover.hide())

        settings_frame = tk.Frame(self.options_container, name="options", bg="black")
        settings_frame.pack(fill="x", pady=(0, 10))

        appearance_section = tk.Frame(settings_frame, bg="black")
        appearance_section.pack(side="left", fill="x", expand=True)

        behavior_section = tk.Frame(settings_frame, bg="black")
        behavior_section.pack(side="left", fill="x", expand=True, padx=(20, 0))

        appearance_header = tk.Label(
            appearance_section,
            text="Ticker Appearance",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10, "bold"),
        )
        appearance_header.pack(anchor="w")

        profile_row = tk.Frame(appearance_section, bg="black")
        profile_row.pack(fill="x", pady=(6, 0))

        profile_names = _profile_name_options()
        self.color_profile_var = tk.StringVar(value=DEFAULT_COLOR_PROFILE_NAME)
        profile_label = tk.Label(
            profile_row, text="Profile:", bg="black", fg="lightgray"
        )
        profile_label.pack(side="left")
        profile_menu = tk.OptionMenu(
            profile_row,
            self.color_profile_var,
            *profile_names,
            command=self._apply_color_profile,
        )
        profile_menu.configure(bg="#2f2f2f", fg="white", highlightthickness=0)
        profile_menu["menu"].configure(bg="#2f2f2f", fg="white")
        profile_menu.pack(side="left", padx=(6, 0))
        self.profile_menu = profile_menu
        self._refresh_profile_menu()

        speed_row = tk.Frame(appearance_section, bg="black")
        speed_row.pack(fill="x", pady=(6, 0))
        speed_label = tk.Label(speed_row, text="Speed:", bg="black", fg="lightgray")
        speed_label.pack(side="left")
        self.ticker_speed_var = tk.IntVar(value=self.ticker.speed)
        speed_spin = tk.Spinbox(
            speed_row,
            from_=1,
            to=20,
            increment=1,
            width=4,
            textvariable=self.ticker_speed_var,
            command=self._apply_speed,
        )
        speed_spin.pack(side="left", padx=(6, 0))
        speed_spin.bind("<FocusOut>", self._apply_speed)
        speed_spin.bind("<Return>", self._apply_speed)

        color_row = tk.Frame(appearance_section, bg="black")
        color_row.pack(fill="x", pady=(6, 0))
        self.ticker_bg_var = tk.StringVar(value=str(self.ticker["bg"]))
        self.ticker_fg_var = tk.StringVar(
            value=self.ticker.itemcget(self.ticker.message_item, "fill")
        )
        bg_button = tk.Button(
            color_row,
            text="Background Color…",
            command=lambda: self._choose_color("background"),
        )
        bg_button.pack(side="left")
        fg_button = tk.Button(
            color_row,
            text="Text Color…",
            command=lambda: self._choose_color("text"),
        )
        fg_button.pack(side="left", padx=6)

        reset_row = tk.Frame(appearance_section, bg="black")
        reset_row.pack(fill="x", pady=(8, 0))
        reset_button = tk.Button(
            reset_row, text="Reset Settings", command=self._reset_settings
        )
        reset_button.pack(side="left")

        behavior_header = tk.Label(
            behavior_section,
            text="Behavior & Timing",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10, "bold"),
        )
        behavior_header.pack(anchor="w")

        debug_row = tk.Frame(behavior_section, bg="black")
        debug_row.pack(fill="x", pady=(6, 0))
        self.debug_check = tk.Checkbutton(
            debug_row,
            text="Debug Logs",
            variable=self.debug_var,
            command=self._toggle_debug_mode,
            bg="black",
            fg="lightgray",
            selectcolor="#202020",
            activebackground="black",
            activeforeground="white",
            highlightthickness=0,
        )
        self.debug_check.pack(side="left")
        self.litellm_debug_check = tk.Checkbutton(
            debug_row,
            text="LiteLLM Debug",
            variable=self.litellm_debug_var,
            command=self._toggle_litellm_debug,
            bg="black",
            fg="lightgray",
            selectcolor="#202020",
            activebackground="black",
            activeforeground="white",
            highlightthickness=0,
        )
        self.litellm_debug_check.pack(side="left", padx=10)

        history_row = tk.Frame(behavior_section, bg="black")
        history_row.pack(fill="x", pady=(6, 0))
        self.historical_cache_check = tk.Checkbutton(
            history_row,
            text="Keep 24h History",
            variable=self.historical_cache_var,
            command=self._toggle_historical_cache,
            bg="black",
            fg="lightgray",
            selectcolor="#202020",
            activebackground="black",
            activeforeground="white",
            highlightthickness=0,
        )
        self.historical_cache_check.pack(side="left")

        auto_row = tk.Frame(behavior_section, bg="black")
        auto_row.pack(fill="x", pady=(6, 0))
        self.auto_refresh_check = tk.Checkbutton(
            auto_row,
            text="Auto Refresh",
            variable=self.auto_refresh_var,
            command=self._toggle_auto_refresh,
            bg="black",
            fg="lightgray",
            selectcolor="#202020",
            activebackground="black",
            activeforeground="white",
            highlightthickness=0,
        )
        self.auto_refresh_check.pack(side="left")
        refresh_label = tk.Label(
            auto_row, text="Interval (min):", bg="black", fg="lightgray"
        )
        refresh_label.pack(side="left", padx=(10, 2))
        self.auto_refresh_spin = tk.Spinbox(
            auto_row,
            from_=1,
            to=180,
            width=4,
            textvariable=self.auto_refresh_minutes_var,
            command=self._update_auto_refresh_minutes,
        )
        self.auto_refresh_spin.pack(side="left")
        self.auto_refresh_spin.bind("<FocusOut>", self._update_auto_refresh_minutes)
        self.auto_refresh_spin.bind("<Return>", self._update_auto_refresh_minutes)

        refresh_status_row = tk.Frame(auto_row, bg="black")
        refresh_status_row.pack(side="left", padx=(16, 0))

        self.next_refresh_var = tk.StringVar(value="Next refresh: --:--")
        next_refresh_label = tk.Label(
            refresh_status_row,
            textvariable=self.next_refresh_var,
            bg="black",
            fg="#89CFF0",
            font=("Segoe UI", 10, "italic"),
        )
        next_refresh_label.pack(side="left")

        self.last_refresh_var = tk.StringVar(value="Last refresh: pending")
        last_refresh_label = tk.Label(
            refresh_status_row,
            textvariable=self.last_refresh_var,
            bg="black",
            fg="#89CFF0",
            font=("Segoe UI", 10, "italic"),
        )
        last_refresh_label.pack(side="left", padx=(12, 0))

        self._update_last_refresh_label()

        watch_row = tk.Frame(behavior_section, bg="black")
        watch_row.pack(fill="x", pady=(6, 0))
        self.background_watch_check = tk.Checkbutton(
            watch_row,
            text="Background Watch",
            variable=self.background_watch_var,
            command=self._toggle_background_watch,
            bg="black",
            fg="lightgray",
            selectcolor="#202020",
            activebackground="black",
            activeforeground="white",
            highlightthickness=0,
        )
        self.background_watch_check.pack(side="left")
        threshold_label = tk.Label(
            watch_row,
            text="Auto-refresh at:",
            bg="black",
            fg="lightgray",
        )
        threshold_label.pack(side="left", padx=(10, 2))
        self.background_watch_threshold_spin = tk.Spinbox(
            watch_row,
            from_=1,
            to=999,
            width=4,
            textvariable=self.background_watch_threshold_var,
            command=self._apply_background_watch_threshold,
        )
        self.background_watch_threshold_spin.pack(side="left")
        self.background_watch_threshold_spin.bind(
            "<FocusOut>", self._apply_background_watch_threshold
        )
        self.background_watch_threshold_spin.bind(
            "<Return>", self._apply_background_watch_threshold
        )
        threshold_suffix = tk.Label(
            watch_row, text="unseen headlines", bg="black", fg="lightgray"
        )
        threshold_suffix.pack(side="left", padx=(4, 0))
        self.new_headlines_label = tk.Label(
            watch_row,
            textvariable=self.new_headlines_var,
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10, "italic"),
        )
        self.new_headlines_label.pack(side="left", padx=(12, 0))

        timezone_row = tk.Frame(behavior_section, bg="black")
        timezone_row.pack(fill="x", pady=(6, 0))
        timezone_label = tk.Label(
            timezone_row,
            text="Time Zone:",
            bg="black",
            fg="lightgray",
        )
        timezone_label.pack(side="left")
        self.timezone_var = tk.StringVar(value=self._timezone_name)
        self.timezone_menu = tk.OptionMenu(
            timezone_row,
            self.timezone_var,
            *self._timezone_options,
        )
        self.timezone_menu.configure(bg="#2f2f2f", fg="white", highlightthickness=0)
        self.timezone_menu["menu"].configure(bg="#2f2f2f", fg="white")
        self.timezone_menu.pack(side="left", padx=(6, 0))
        self._refresh_timezone_menu()
        self.timezone_var.trace_add("write", self._on_timezone_change)

        self.log_visible = False
        self.log_frame = tk.Frame(self, bg="black")
        log_scroll = tk.Scrollbar(self.log_frame)
        log_scroll.pack(side="right", fill="y")
        self.log_text = tk.Text(
            self.log_frame,
            wrap="word",
            bg="#101010",
            fg="lightgray",
            height=10,
            state="disabled",
            yscrollcommand=log_scroll.set,
            font=("Consolas", 11),
        )
        self.log_text.pack(fill="both", expand=True)
        log_scroll.config(command=self.log_text.yview)
        self._append_log_line("Logs:")

        self._apply_settings_from_store()
        self._loading_settings = False
        self._save_settings()
        self._log_startup_report()
        self.after(0, self.refresh_headlines)
        self.after(0, self._flush_log_buffer)
        self.after(0, self._update_redis_meter)
        current_geometry = self.geometry()
        if current_geometry:
            self._last_geometry = current_geometry
            self.settings["window_geometry"] = current_geometry
        self._geometry_tracking_ready = True
        self._schedule_auto_refresh()

    def clear_cache(self) -> None:
        """Trigger a background task to clear the Redis headline cache."""
        threading.Thread(target=self._clear_cache_worker, daemon=True).start()

    def _clear_cache_worker(self) -> None:
        success, message = clear_cached_headlines()
        level = logging.INFO if success else logging.WARNING
        self.after(0, lambda: self._handle_cache_clear_result(message, level))

    def _handle_cache_clear_result(self, message: str, level: int) -> None:
        self._log_status(message, level=level)
        self._update_redis_meter()

    def _open_redis_stats(self) -> None:
        if self._loading_redis_stats:
            return
        if not REDIS_URL:
            messagebox.showinfo(
                "Redis Statistics",
                "Redis caching is disabled. Set REDIS_URL to enable diagnostics.",
            )
            return
        self._loading_redis_stats = True
        try:
            self.redis_stats_btn.config(state=tk.DISABLED)
        except Exception:
            logger.debug("Unable to disable Redis stats button before loading.")
        threading.Thread(
            target=self._load_redis_stats_worker,
            daemon=True,
        ).start()

    def _load_redis_stats_worker(self) -> None:
        try:
            stats = collect_redis_statistics()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to collect Redis statistics.")
            stats = RedisStatistics(
                cache_configured=bool(REDIS_URL),
                available=False,
                cache_key=CACHE_KEY,
                key_present=False,
                warnings=[f"Unable to collect Redis statistics: {exc}"],
                error=str(exc),
            )
        self.after(0, lambda: self._handle_redis_stats_ready(stats))

    def _handle_redis_stats_ready(self, stats: RedisStatistics) -> None:
        self._loading_redis_stats = False
        button_state = tk.NORMAL if REDIS_URL else tk.DISABLED
        try:
            self.redis_stats_btn.config(state=button_state)
        except Exception:
            logger.debug("Unable to restore Redis stats button state.")

        if not stats.available:
            detail = "\n".join(stats.warnings) if stats.warnings else "Redis cache unavailable."
            messagebox.showwarning("Redis Statistics", detail)
            return

        if self._redis_stats_window and self._redis_stats_window.winfo_exists():
            self._redis_stats_window.update_stats(stats)
            self._redis_stats_window.deiconify()
            self._redis_stats_window.lift()
            self._redis_stats_window.focus_force()
            return

        try:
            self._redis_stats_window = RedisStatsWindow(
                self,
                stats,
                timezone_name=self._timezone_name,
                timezone_obj=self._timezone,
                on_close=self._on_redis_stats_closed,
            )
        except Exception:
            self._redis_stats_window = None
            logger.exception("Failed to open Redis stats window.")
            messagebox.showerror(
                "Redis Statistics",
                "Unable to open Redis statistics window. See logs for details.",
            )

    def _on_redis_stats_closed(self) -> None:
        self._redis_stats_window = None
        if not hasattr(self, "redis_stats_btn"):
            return
        if self._loading_redis_stats:
            self.redis_stats_btn.config(state=tk.DISABLED)
            return
        self.redis_stats_btn.config(state=tk.NORMAL if REDIS_URL else tk.DISABLED)

    def _update_redis_meter(self) -> None:
        client = get_redis_client()
        if client is None:
            self.redis_meter_var.set("Redis: OFF")
            self.redis_meter_label.config(fg="#FF6B6B")
            if hasattr(self, "redis_stats_btn"):
                state = tk.DISABLED if not REDIS_URL else (
                    tk.DISABLED if self._loading_redis_stats else tk.NORMAL
                )
                self.redis_stats_btn.config(state=state)
            self._refresh_history_controls_state()
            return

        try:
            client.ping()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - redis ping failure
            logger.debug("Redis ping failed; treating cache as unavailable: %s", exc)
            self.redis_meter_var.set("Redis: OFF")
            self.redis_meter_label.config(fg="#FF6B6B")
            if hasattr(self, "redis_stats_btn"):
                state = tk.DISABLED if not REDIS_URL else (
                    tk.DISABLED if self._loading_redis_stats else tk.NORMAL
                )
                self.redis_stats_btn.config(state=state)
            self._refresh_history_controls_state()
            return

        self.redis_meter_var.set("Redis: ON")
        self.redis_meter_label.config(fg="#32CD32")
        if hasattr(self, "redis_stats_btn"):
            state = tk.DISABLED if not REDIS_URL else (
                tk.DISABLED if self._loading_redis_stats else tk.NORMAL
            )
            self.redis_stats_btn.config(state=state)
        self._refresh_history_controls_state()

    def refresh_headlines(self, force_refresh: bool = False) -> None:
        if self._history_mode:
            self._exit_history_mode(trigger_refresh=False)
        self._log_status("Fetching AI headlines…")
        self.next_refresh_var.set("Refreshing…")
        self._update_status_summary()
        threading.Thread(
            target=self._refresh_worker, args=(force_refresh,), daemon=True
        ).start()

    def _refresh_worker(self, force_refresh: bool) -> None:
        logger.info("Refreshing headlines (force_refresh=%s)", force_refresh)
        try:
            fetched_at = datetime.now()
            headlines, from_cache, cached_ticker = fetch_headlines(
                force_refresh=force_refresh
            )
            if from_cache:
                ticker_text = cached_ticker or build_ticker_text(headlines)
                should_update_cache = bool(headlines) and not cached_ticker
            else:
                ticker_text = build_ticker_text(headlines)
                should_update_cache = bool(headlines)
            if should_update_cache:
                persist_headlines_with_ticker(headlines, ticker_text)
        except Exception as exc:
            logger.exception("Failed to update headlines:")
            self.after(0, lambda: self._handle_fetch_error(exc))
            return

        self.after(
            0,
            lambda: self._handle_refresh_result(
                headlines=headlines,
                ticker_text=ticker_text,
                from_cache=from_cache,
                fetched_at=fetched_at,
            ),
        )

    def _handle_refresh_result(
        self,
        *,
        headlines: List[Headline],
        ticker_text: str,
        from_cache: bool,
        fetched_at: datetime,
    ) -> None:
        self._pending_new_headlines = 0
        self._last_reported_pending = 0
        self._background_candidate_keys.clear()
        self._update_background_watch_label()
        self._last_refresh_time = fetched_at
        self._update_content(
            headlines=headlines, ticker_text=ticker_text, from_cache=from_cache
        )
        self._update_redis_meter()
        self._update_last_refresh_label()

    def _headline_with_timezone(self, headline: Headline) -> Headline:
        formatted_time, formatted_iso = self._compute_localized_times(headline)
        updates: Dict[str, str] = {}
        if formatted_time is not None:
            updates["published_time"] = formatted_time
        if formatted_iso is not None:
            updates["published_at"] = formatted_iso
        if updates:
            return replace(headline, **updates)
        return headline

    def _compute_localized_times(
        self, headline: Headline
    ) -> tuple[Optional[str], Optional[str]]:
        timestamp_utc = _parse_iso8601_utc(headline.published_at)
        if timestamp_utc is not None:
            localized_label, localized_iso = _format_localized_timestamp(
                timestamp_utc, self._timezone
            )
            return localized_label, localized_iso

        if isinstance(headline.published_time, str):
            label = headline.published_time.strip()
            if label:
                tz_name = datetime.now(self._timezone).tzname()
                if tz_name and not label.endswith(tz_name):
                    return f"{label} {tz_name}", None
                return label, None
        return None, headline.published_at

    def _group_headlines_by_age(
        self, entries: Sequence[tuple[int, Headline]]
    ) -> List[tuple[str, List[tuple[int, Headline, Optional[float]]]]]:
        """Delegate to modular rendering.group_headlines_by_age."""
        return _group_headlines_by_age_fn(entries)

    def _headline_age_minutes(
        self, headline: Headline, now_utc: datetime
    ) -> Optional[float]:
        """Delegate to modular rendering.headline_age_minutes."""
        return _headline_age_minutes_fn(headline, now_utc)

    def _resolve_age_bucket(self, age_minutes: Optional[float]) -> str:
        """Delegate to modular rendering.resolve_age_bucket."""
        return _resolve_age_bucket_fn(age_minutes)

    def _format_relative_age(self, age_minutes: Optional[float]) -> Optional[str]:
        """Delegate to modular rendering.format_relative_age."""
        return _format_relative_age_fn(age_minutes)

    def _compose_metadata_parts(
        self, localized: Headline, relative_label: Optional[str]
    ) -> List[str]:
        parts: List[str] = []
        if isinstance(localized.source, str):
            source_label = localized.source.strip()
            if source_label:
                parts.append(source_label)
        if isinstance(localized.published_time, str):
            published_label = localized.published_time.strip()
            if published_label:
                parts.append(published_label)
        if relative_label:
            parts.append(relative_label)
        if parts:
            return parts
        if isinstance(localized.section, str):
            section_label = localized.section.strip()
            if section_label:
                return [section_label]
        return ["Unknown source"]

    def _clear_headline_list(self) -> None:
        self.listbox.configure(state="normal")
        self.listbox.delete("1.0", tk.END)
        self.listbox.configure(state="disabled")
        self._listbox_line_to_headline.clear()
        self._listbox_line_details.clear()
        self._listbox_line_prefix.clear()
        self._listbox_line_metadata.clear()
        self._row_tag_to_line.clear()
        self._row_tag_to_headline.clear()
        self._line_to_row_tag.clear()
        self._listbox_hover_line = None
        self._listbox_last_tooltip_text = None
        self._selected_line = None
        self._clear_listbox_selection()
        if hasattr(self, "_listbox_tooltip"):
            self._listbox_tooltip.hide()
        # Refresh action buttons for current selection state.
        self._refresh_mute_button_state()

    def _ensure_color_tag(self, color: str) -> str:
        tag = self._listbox_color_tags.get(color)
        if tag is not None:
            return tag
        tag = f"color_{len(self._listbox_color_tags)}"
        self.listbox.tag_configure(tag, foreground=color)
        self._listbox_color_tags[color] = tag
        return tag

    def _ensure_line_break(self) -> None:
        try:
            last_char = self.listbox.get("end-1c")
        except tk.TclError:
            return
        if not last_char or last_char == "\n":
            return
        self.listbox.insert("end", "\n")

    def _append_group_label(self, text: str) -> None:
        self.listbox.configure(state="normal")
        self._ensure_line_break()
        self.listbox.insert("end", text, ("group",))
        self.listbox.insert("end", "\n")
        self.listbox.configure(state="disabled")

    def _append_headline_line(
        self,
        *,
        display_index: int,
        localized: Headline,
        metadata_text: str,
        relative_label: Optional[str],
        row_color: Optional[str],
        original_idx: int,
    ) -> None:
        color_tag = self._ensure_color_tag(row_color or self.listbox_default_fg)
        prefix_text = f"{display_index}. {localized.title}"
        row_tag = f"row_{len(self._row_tag_to_headline)}"
        self.listbox.configure(state="normal")
        self._ensure_line_break()
        insertion_index = self.listbox.index("end")
        self.listbox.insert("end", prefix_text, ("title", color_tag, row_tag))
        metadata_with_dash = f" — {metadata_text}"
        self.listbox.insert("end", metadata_with_dash, ("metadata", row_tag))
        self.listbox.insert("end", "\n", (row_tag,))
        ranges = self.listbox.tag_ranges(row_tag)
        if ranges:
            start_index = str(ranges[0])
        else:
            start_index = str(insertion_index)
        try:
            line_no = int(float(start_index.split(".")[0]))
        except (ValueError, IndexError):
            line_no = int(float(self.listbox.index("end-1c").split(".")[0]))
        self.listbox.configure(state="disabled")
        self._row_tag_to_headline[row_tag] = original_idx
        self._row_tag_to_line[row_tag] = line_no
        self._line_to_row_tag[line_no] = row_tag
        self._listbox_line_to_headline[line_no] = original_idx
        self._listbox_line_details[line_no] = HeadlineTooltipData(
            headline=localized,
            relative_age=relative_label,
            display_index=display_index,
            row_kind="title",
        )
        self._listbox_line_prefix[line_no] = len(prefix_text)
        self._listbox_line_metadata[line_no] = metadata_with_dash

    def _append_message_line(self, text: str) -> None:
        self.listbox.configure(state="normal")
        self._ensure_line_break()
        self.listbox.insert("end", text, ("message",))
        self.listbox.insert("end", "\n")
        self.listbox.configure(state="disabled")

    def _clear_listbox_selection(self) -> None:
        self.listbox.configure(state="normal")
        self.listbox.tag_remove("selected", "1.0", tk.END)
        self.listbox.configure(state="disabled")
        self._selected_line = None

    def _select_listbox_line(self, line: int) -> None:
        line_count = int(float(self.listbox.index("end-1c").split(".")[0]))
        if line < 1 or line > line_count:
            return
        self.listbox.configure(state="normal")
        self.listbox.tag_remove("selected", "1.0", tk.END)
        self.listbox.tag_add("selected", f"{line}.0", f"{line}.end")
        self.listbox.tag_raise("selected")
        self.listbox.configure(state="disabled")
        self._selected_line = line

    def _update_content(
        self,
        headlines: List[Headline],
        ticker_text: str,
        from_cache: bool = False,
        *,
        reschedule: bool = True,
        log_status: bool = True,
        update_tickers: Optional[bool] = None,
    ) -> None:
        if update_tickers is None:
            update_tickers = not self._history_mode
        if not self._history_mode:
            self._last_live_payload = (
                list(headlines),
                ticker_text,
                from_cache,
            )
        self._raw_headlines = list(headlines)
        self._raw_total_headlines = len(self._raw_headlines)
        self._last_headline_from_cache = from_cache
        self._base_source_label = "cache" if from_cache else "live"
        self._apply_exclusion_filter_to_state(
            reschedule=reschedule,
            log_status=log_status,
            update_tickers=update_tickers,
        )
        if self._raw_total_headlines:
            logger.info(
                "Loaded %s headlines (%s source).",
                self._raw_total_headlines,
                self._base_source_label,
            )
        else:
            logger.info("Headline list empty before exclusions.")

    def _apply_exclusion_filter_to_state(
        self,
        *,
        reschedule: bool,
        log_status: bool,
        update_tickers: Optional[bool] = None,
    ) -> None:
        if update_tickers is None:
            update_tickers = not self._history_mode
        filtered = self._filter_headlines(self._raw_headlines)
        excluded = self._raw_total_headlines - len(filtered)
        self._last_excluded_count = excluded
        self.headlines = filtered

        if filtered:
            ticker_text = build_ticker_text(filtered)
        elif self._raw_total_headlines and excluded == self._raw_total_headlines:
            ticker_text = "All headlines filtered by exclusion terms."
        else:
            ticker_text = "No headlines available right now."

        summary_parts: List[str] = []
        if filtered:
            summary_parts.append(ticker_text)
        else:
            summary_parts.append(ticker_text)
        if excluded:
            summary_parts.append(f"{excluded} filtered by exclusion terms.")

        self._current_ticker_text = ticker_text
        self._base_total_headlines = len(filtered)
        self._base_summary_text = " | ".join(part for part in summary_parts if part)

        self._refresh_section_filter_menu(filtered)
        self._render_filtered_headlines(
            reschedule=reschedule,
            log_status=log_status,
            update_tickers=update_tickers,
        )

        if self._heatmap_window and self._heatmap_window.winfo_exists():
            self._heatmap_window.update_data(self.headlines)

        if excluded:
            logger.info("Excluded %s headline(s) via exclusion terms.", excluded)

    def _render_filtered_headlines(
        self,
        *,
        reschedule: bool = False,
        log_status: bool = False,
        update_tickers: Optional[bool] = None,
    ) -> None:
        if update_tickers is None:
            update_tickers = not self._history_mode
        self._clear_headline_list()

        filtered_entries = self._filtered_entries()
        filters_active = self._filters_active()
        total_count = self._base_total_headlines
        matched_count = len(filtered_entries)

        if filtered_entries:
            grouped = self._group_headlines_by_age(filtered_entries)
            display_idx = 1
            localized_cache: Dict[int, Headline] = {}
            filtered_headlines: List[Headline] = []
            full_headlines: List[Headline] = []
            for label, items in grouped:
                self._append_group_label(f"-- {label} --")
                for original_idx, headline, age_minutes in items:
                    localized = localized_cache.get(original_idx)
                    if localized is None:
                        localized = self._headline_with_timezone(headline)
                        localized_cache[original_idx] = localized
                    relative_label = self._format_relative_age(age_minutes)
                    metadata_parts = self._compose_metadata_parts(
                        localized, relative_label
                    )

                    row_color = headline_highlight_color(localized)

                    metadata_text = " • ".join(metadata_parts)
                    self._append_headline_line(
                        display_index=display_idx,
                        localized=localized,
                        metadata_text=metadata_text,
                        relative_label=relative_label,
                        row_color=row_color,
                        original_idx=original_idx,
                    )
                    display_idx += 1

            refresh_fallback = (
                self._last_refresh_time.strftime("%H:%M")
                if self._last_refresh_time
                else datetime.now().strftime("%H:%M")
            )
            localized_headlines = [
                localized_cache.get(idx) or self._headline_with_timezone(headline)
                for idx, headline in filtered_entries
            ]
            filtered_headlines = localized_headlines
            for localized in localized_headlines:
                display_time = localized.published_time or refresh_fallback
                full_headlines.append(
                    replace(localized, title=f"{localized.title} [{display_time}]")
                )
            if update_tickers:
                self.ticker.set_items(filtered_headlines)
                self.full_ticker.set_items(full_headlines)
                self._live_ticker_items = list(filtered_headlines)
                self._live_full_ticker_items = list(full_headlines)
            self._schedule_relative_age_refresh()
        else:
            if filters_active and total_count:
                message = "No headlines match current filters."
            elif (
                not filters_active
                and self._raw_total_headlines
                and self._last_excluded_count == self._raw_total_headlines
            ):
                message = "All headlines filtered by exclusion terms."
            elif self._last_excluded_count and self._raw_total_headlines:
                message = (
                    "No headlines available right now (some filtered by exclusion terms)."
                )
            else:
                message = "No headlines available right now."
            self._append_message_line(message)
            if update_tickers:
                self.ticker.set_text(message)
                self.full_ticker.set_text(message)
                self._live_ticker_items = []
                self._live_full_ticker_items = []
            self._cancel_relative_age_refresh()

        if log_status:
            if total_count == 0:
                self._log_status("No headlines available right now.")
            elif filters_active:
                if matched_count == 0:
                    self._log_status("No headlines match current filters.")
                else:
                    summary_bits = [
                        f"{matched_count}/{total_count} headlines match current filters."
                    ]
                    if self._base_summary_text:
                        summary_bits.append(self._base_summary_text)
                    self._log_status(" | ".join(summary_bits))
            else:
                summary = self._base_summary_text or f"Loaded {total_count} headlines."
                self._log_status(
                    f"{total_count} headlines ({self._base_source_label}) | {summary}"
                )
        self._recompute_background_pending()
        self._refresh_mute_button_state()
        if reschedule:
            self._schedule_auto_refresh()

    def _restore_live_tickers(self) -> None:
        if self._history_mode:
            return
        if self._live_ticker_items:
            self.ticker.set_items(self._live_ticker_items)
        else:
            self.ticker.set_text(self._current_ticker_text)
        if self._live_full_ticker_items:
            self.full_ticker.set_items(self._live_full_ticker_items)
        else:
            self.full_ticker.set_text(self._current_ticker_text)

    def _cancel_relative_age_refresh(self) -> None:
        if self._relative_age_job is None:
            return
        try:
            self.after_cancel(self._relative_age_job)
        except tk.TclError:
            pass
        self._relative_age_job = None

    def _schedule_relative_age_refresh(self) -> None:
        self._cancel_relative_age_refresh()
        if not self._listbox_line_to_headline:
            return
        self._relative_age_job = self.after(60_000, self._refresh_relative_age_labels)

    def _refresh_relative_age_labels(self) -> None:
        self._relative_age_job = None
        if not self._listbox_line_to_headline:
            return
        now_utc = datetime.now(timezone.utc)
        updated_any = False
        for line, original_idx in list(self._listbox_line_to_headline.items()):
            if original_idx < 0 or original_idx >= len(self.headlines):
                continue
            headline = self.headlines[original_idx]
            localized = self._headline_with_timezone(headline)
            age_minutes = self._headline_age_minutes(headline, now_utc)
            relative_label = self._format_relative_age(age_minutes)
            context = self._listbox_line_details.get(line)
            display_index = (
                context.display_index if context and context.display_index is not None else original_idx + 1
            )
            row_color = headline_highlight_color(localized)
            metadata_parts = self._compose_metadata_parts(localized, relative_label)
            metadata_text = " • ".join(metadata_parts)
            metadata_with_dash = f" — {metadata_text}"
            prefix_len = self._listbox_line_prefix.get(line, 0)
            insert_index = f"{line}.0 + {prefix_len}c"
            line_end = f"{line}.end"
            self.listbox.configure(state="normal")
            self.listbox.delete(insert_index, line_end)
            row_tag = self._line_to_row_tag.get(line)
            metadata_tags: tuple[str, ...]
            if row_tag:
                metadata_tags = ("metadata", row_tag)
            else:
                metadata_tags = ("metadata",)
            self.listbox.insert(insert_index, metadata_with_dash, metadata_tags)
            color_tag = self._ensure_color_tag(row_color or self.listbox_default_fg)
            prefix_start = f"{line}.0"
            prefix_end = f"{line}.0 + {prefix_len}c"
            for tag in self._listbox_color_tags.values():
                self.listbox.tag_remove(tag, prefix_start, prefix_end)
            self.listbox.tag_add(color_tag, prefix_start, prefix_end)
            self.listbox.configure(state="disabled")
            self._listbox_line_metadata[line] = metadata_with_dash
            self._listbox_line_details[line] = HeadlineTooltipData(
                headline=localized,
                relative_age=relative_label,
                display_index=display_index,
                row_kind="title",
            )
            updated_any = True
        if updated_any:
            self._schedule_relative_age_refresh()

    def _reapply_exclusion_filters(self, *, log_status: bool) -> None:
        self._apply_exclusion_filter_to_state(reschedule=False, log_status=log_status)

    def _apply_exclusion_terms(self, event: Optional[tk.Event] = None) -> Optional[str]:
        terms_list, terms_set = self._normalise_exclusion_terms(
            self.exclude_terms_var.get()
        )
        self.exclude_terms_var.set(", ".join(terms_list))

        if terms_set == self._exclusion_terms and terms_list == self.settings.get(
            "headline_exclusions", []
        ):
            if event is not None and getattr(event, "keysym", None) == "Return":
                return "break"
            return None

        self._exclusion_terms = terms_set
        self.settings["headline_exclusions"] = terms_list
        self._save_settings()
        self._reapply_exclusion_filters(log_status=True)
        if event is not None and getattr(event, "keysym", None) == "Return":
            return "break"
        return None

    def _clear_exclusion_terms(self) -> None:
        if not self._exclusion_terms and not self.exclude_terms_var.get().strip():
            return
        self.exclude_terms_var.set("")
        self._apply_exclusion_terms()

    def _filter_headlines(self, headlines: Sequence[Headline]) -> List[Headline]:
        if not headlines:
            return []
        if not self._exclusion_terms:
            return list(headlines)
        filtered: List[Headline] = []
        for item in headlines:
            haystack_parts = [
                item.title,
                item.source,
                item.section,
                item.published_time,
                item.published_at,
                item.url,
            ]
            haystack = " ".join(
                part.strip()
                for part in haystack_parts
                if isinstance(part, str) and part.strip()
            ).lower()
            if any(term in haystack for term in self._exclusion_terms):
                continue
            filtered.append(item)
        return filtered

    def _normalise_exclusion_terms(self, source: Any) -> tuple[List[str], Set[str]]:
        candidates: List[str] = []
        if isinstance(source, str):
            candidates.extend(self._split_exclusion_string(source))
        elif isinstance(source, Sequence) and not isinstance(source, (str, bytes)):
            for item in source:
                if isinstance(item, str):
                    candidates.extend(self._split_exclusion_string(item))

        unique_terms: List[str] = []
        seen: Set[str] = set()
        for candidate in candidates:
            cleaned = candidate.strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            unique_terms.append(cleaned)
            seen.add(lowered)

        return unique_terms, seen

    def _split_exclusion_string(self, text: str) -> List[str]:
        """Split a free-form exclusion string into normalized terms.

        Accepts commas, semicolons, and whitespace as separators. Returns a
        list of terms in their original order, trimmed and lowercased,
        without empty entries.
        """
        if not isinstance(text, str):
            return []
        raw = re.split(r"[;,]|\s+", text.strip())
        terms = [t.strip().lower() for t in raw if t and t.strip()]
        return terms
    def _resolve_selected_headline(self) -> Optional[Headline]:
        """Resolve the Headline object for the currently selected list row."""
        line = self._selected_line
        if line is None:
            return None
        detail = self._listbox_line_details.get(line)
        if detail is not None and isinstance(detail.headline, Headline):
            return detail.headline
        index = self._listbox_line_to_headline.get(line)
        if index is None or index < 0 or index >= len(self.headlines):
            return None
        return self.headlines[index]

    def _refresh_mute_button_state(self) -> None:
        """Enable or disable 'Mute' buttons based on current selection suitability."""
        if not hasattr(self, "mute_source_btn") or not hasattr(
            self, "mute_keyword_btn"
        ):
            return
        headline = self._resolve_selected_headline()
        enable_source = False
        enable_keyword = False
        if headline is not None:
            url_val = headline.url if isinstance(headline.url, str) else ""
            src_val = headline.source if isinstance(headline.source, str) else ""
            enable_source = bool(url_val.strip() or src_val.strip())
            title_val = headline.title if isinstance(headline.title, str) else ""
            enable_keyword = bool(self._extract_keyword_for_mute(title_val))
        try:
            self.mute_source_btn.config(
                state=(tk.NORMAL if enable_source else tk.DISABLED)
            )
            self.mute_keyword_btn.config(
                state=(tk.NORMAL if enable_keyword else tk.DISABLED)
            )
        except Exception:
            logger.debug("Unable to update mute action button state.")

    def _extract_keyword_for_mute(self, title: str) -> Optional[str]:
        """Derive a simple, useful keyword from a headline title for muting."""
        if not isinstance(title, str):
            return None
        tokens = re.findall(r"[A-Za-z0-9+#\\-]{3,}", title)
        for token in tokens:
            lower = token.lower()
            if lower in _MUTE_STOPWORDS:
                continue
            if lower.isdigit():
                continue
            if len(lower) < 4 and lower not in {"ai", "usa", "uk"}:
                continue
            return token
        return None

    def _add_exclusion_term(self, term: str, *, show_feedback: bool = True) -> bool:
        """Append a term to exclusions asynchronously and re-render on completion."""
        cleaned = (term or "").strip()
        if not cleaned:
            return False

        # Disable actions and show a short status message to keep UI responsive.
        try:
            if hasattr(self, "mute_source_btn"):
                self.mute_source_btn.config(state=tk.DISABLED)
            if hasattr(self, "mute_keyword_btn"):
                self.mute_keyword_btn.config(state=tk.DISABLED)
        except Exception:
            pass
        self._log_status("Applying exclusion…")

        current_text = (
            self.exclude_terms_var.get() if hasattr(self, "exclude_terms_var") else ""
        )

        def worker() -> None:
            combined = f"{current_text}, {cleaned}" if current_text.strip() else cleaned
            terms_list, terms_set = self._normalise_exclusion_terms(combined)
            is_changed = terms_set != self._exclusion_terms

            def finalize() -> None:
                if not is_changed:
                    if show_feedback:
                        self._log_status(
                            f"Exclusion term already present: '{cleaned}'."
                        )
                    self._refresh_mute_button_state()
                    return
                self._exclusion_terms = terms_set
                self.settings["headline_exclusions"] = terms_list
                if hasattr(self, "exclude_terms_var"):
                    self.exclude_terms_var.set(", ".join(terms_list))
                self._save_settings()
                # Re-render on the main thread.
                self._reapply_exclusion_filters(log_status=True)
                self._refresh_mute_button_state()
                if show_feedback:
                    self._log_status(f"Added exclusion term: '{cleaned}'.")

            self.after(0, finalize)

        threading.Thread(target=worker, daemon=True).start()
        return True

    def _mute_selected_source(self) -> None:
        """Mute the source (final article domain or label) of the selection."""
        headline = self._resolve_selected_headline()
        if headline is None:
            return

        # Resolve the final URL in a background thread to avoid UI blocking.
        def worker() -> None:
            term: Optional[str] = None
            url_val = headline.url if isinstance(headline.url, str) else ""
            if url_val.strip():
                try:
                    # Lightweight final-URL resolution via shared HTTP client
                    from .http_client import resolve_final_url
                    resolved = resolve_final_url(url_val, timeout=8)
                    parsed = urlparse(resolved)
                    netloc = parsed.netloc or ""
                    # Normalize domain: strip auth/port and www prefix
                    netloc = netloc.split("@")[-1].split(":")[0].lower()
                    if netloc.startswith("www."):
                        netloc = netloc[4:]
                    # Avoid muting NewsNow redirector domains
                    redirect_suffixes = ("newsnow.com", "newsnow.co.uk")
                    if netloc and not any(netloc.endswith(s) for s in redirect_suffixes):
                        term = netloc
                except Exception:
                    # Fall back to deriving from existing helpers
                    term = None

            if not term:
                try:
                    term = _derive_source_term_fn(headline)
                except Exception:
                    term = None

            def finalize() -> None:
                if not term:
                    messagebox.showinfo(
                        "Mute Source",
                        "Unable to derive a source to mute for this item.",
                    )
                    return
                # Apply exclusion on the main thread
                self._add_exclusion_term(term, show_feedback=True)

            self.after(0, finalize)

        threading.Thread(target=worker, daemon=True).start()

    def _mute_selected_keyword(self) -> None:
        """Mute a heuristic keyword derived from the selected headline's title."""
        headline = self._resolve_selected_headline()
        if headline is None:
            return
        title_val = headline.title if isinstance(headline.title, str) else ""
        keyword = self._extract_keyword_for_mute(title_val)
        if not keyword:
            messagebox.showinfo(
                "Mute Keyword", "Unable to derive a keyword to mute from the title."
            )
            return
        self._add_exclusion_term(keyword, show_feedback=True)
        return



    def _on_listbox_click(self, event: tk.Event) -> str:
        try:
            index = self.listbox.index(f"@{event.x},{event.y}")
        except tk.TclError:
            self._clear_listbox_selection()
            return "break"
        line: Optional[int] = None
        for tag in self.listbox.tag_names(index):
            if tag.startswith("row_"):
                candidate = self._row_tag_to_line.get(tag)
                if candidate is not None:
                    line = candidate
                    break
        if line is None:
            try:
                line = int(float(index.split(".")[0]))
            except (ValueError, IndexError):
                line = None
        if line is None:
            self._clear_listbox_selection()
            return "break"
        if line not in self._listbox_line_to_headline:
            for offset in (1, -1, 2, -2, 3, -3):
                probe = line + offset
                if probe in self._listbox_line_to_headline:
                    line = probe
                    break
            else:
                self._clear_listbox_selection()
                return "break"
        self._select_listbox_line(line)
        self.listbox.see(f"{line}.0")
        self._refresh_mute_button_state()
        return "break"

    def _on_listbox_nav(self, delta: int) -> str:
        if not self._listbox_line_to_headline:
            return "break"
        sorted_lines = sorted(self._listbox_line_to_headline.keys())
        if not sorted_lines:
            return "break"
        if self._selected_line is None or self._selected_line not in self._listbox_line_to_headline:
            line = sorted_lines[0] if delta > 0 else sorted_lines[-1]
        else:
            current_index = sorted_lines.index(self._selected_line)
            new_index = current_index + delta
            new_index = max(0, min(len(sorted_lines) - 1, new_index))
            line = sorted_lines[new_index]
        self._select_listbox_line(line)
        self.listbox.see(f"{line}.0")
        self._refresh_mute_button_state()
        return "break"

    def _on_listbox_motion(self, event: tk.Event) -> None:
        if not self._listbox_line_to_headline:
            self._listbox_tooltip.hide()
            self._listbox_hover_line = None
            self._listbox_last_tooltip_text = None
            return
        try:
            index = self.listbox.index(f"@{event.x},{event.y}")
        except tk.TclError:
            self._listbox_tooltip.hide()
            self._listbox_hover_line = None
            self._listbox_last_tooltip_text = None
            return
        line = int(float(index.split(".")[0]))
        context = self._listbox_line_details.get(line)
        candidate_line = line
        candidate_index = index
        if context is None:
            for offset in (-1, 1, -2, 2):
                probe = line + offset
                if probe < 1:
                    continue
                probe_context = self._listbox_line_details.get(probe)
                if probe_context is not None:
                    context = probe_context
                    candidate_line = probe
                    candidate_index = f"{probe}.0"
                    break
        if context is None:
            self._listbox_tooltip.hide()
            self._listbox_hover_line = None
            self._listbox_last_tooltip_text = None
            return
        tooltip_text = compose_headline_tooltip(
            context.headline, relative_age=context.relative_age
        )
        if (
            candidate_line != self._listbox_hover_line
            or tooltip_text != (self._listbox_last_tooltip_text or "")
        ):
            self._listbox_hover_line = candidate_line
            self._listbox_last_tooltip_text = tooltip_text
            coords = self._tooltip_coords(candidate_index, event)
            x_root, y_root = coords
            self._listbox_tooltip.show(tooltip_text, x_root, y_root)
        else:
            coords = self._tooltip_coords(candidate_index, event)
            x_root, y_root = coords
            self._listbox_tooltip.move(x_root, y_root)

    def _on_listbox_leave(self, _event: tk.Event) -> None:
        self._listbox_hover_line = None
        self._listbox_last_tooltip_text = None
        self._listbox_tooltip.hide()

    def _tooltip_coords(self, index: str, event: tk.Event) -> tuple[int, int]:
        try:
            bbox = self.listbox.bbox(index)
        except tk.TclError:
            bbox = None
        if bbox:
            x_pix, y_pix, width, height = bbox
        else:
            return event.x_root, event.y_root

        width = max(width, 1)
        height = max(height, 1)
        widget_root_x = self.listbox.winfo_rootx()
        widget_root_y = self.listbox.winfo_rooty()
        x_root = widget_root_x + x_pix + width + 12
        y_root = widget_root_y + y_pix + height // 2
        return x_root, y_root

    def _request_history_refresh(self) -> None:
        if self._loading_history:
            return
        if not REDIS_URL:
            messagebox.showinfo(
                "History unavailable",
                "Redis caching is disabled. Set REDIS_URL to browse history snapshots.",
            )
            return
        if not bool(self.historical_cache_var.get()):
            messagebox.showinfo(
                "History disabled",
                "Enable the 24h history toggle to start collecting historical snapshots.",
            )
            return
        if get_redis_client() is None:
            messagebox.showwarning(
                "History unavailable",
                "Redis connection is unavailable. Check the Redis URL and retry.",
            )
            return

        self._loading_history = True
        self.history_status_var.set("Loading history snapshots…")
        self.history_reload_btn.config(state=tk.DISABLED)
        self.history_listbox.configure(state=tk.DISABLED)
        self.history_listbox_hover.hide()
        threading.Thread(target=self._history_loader_worker, daemon=True).start()

    def _history_loader_worker(self) -> None:
        error: Optional[str] = None
        try:
            snapshots = load_historical_snapshots()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to load historical snapshots.")
            snapshots = []
            error = str(exc)
        self.after(0, lambda: self._handle_history_loaded(snapshots, error))

    def _handle_history_loaded(
        self, snapshots: Sequence[HistoricalSnapshot], error: Optional[str]
    ) -> None:
        self._loading_history = False
        can_refresh = bool(REDIS_URL) and bool(self.historical_cache_var.get())
        try:
            self.history_reload_btn.config(state=tk.NORMAL if can_refresh else tk.DISABLED)
        except Exception:
            logger.debug("Unable to update history refresh button state.")

        self.history_listbox.configure(state=tk.NORMAL)
        self.history_listbox.delete(0, tk.END)
        self._history_entries = list(snapshots)

        if error:
            self.history_status_var.set(f"History load failed: {error}")
            self.history_listbox.insert(
                tk.END, "Unable to load history snapshots right now."
            )
            self.history_listbox.configure(state=tk.DISABLED)
            return

        if not self._history_entries:
            message = "No cached headlines captured in the last 24 hours."
            self.history_status_var.set(message)
            self.history_listbox.insert(tk.END, message)
            self.history_listbox.configure(state=tk.DISABLED)
            self.history_listbox_hover.hide()
            if self._history_mode:
                self._exit_history_mode(trigger_refresh=False)
            return

        self.history_listbox.configure(state=tk.NORMAL)
        for snapshot in self._history_entries:
            self.history_listbox.insert(tk.END, self._format_history_entry(snapshot))
        self.history_status_var.set(
            f"{len(self._history_entries)} snapshots loaded (newest first). Select to view."
        )
        self.history_listbox.selection_clear(0, tk.END)
        self.history_listbox_hover.hide()

        if self._history_mode and self._history_active_snapshot is not None:
            active_key = self._history_active_snapshot.key
            keys = [entry.key for entry in self._history_entries]
            if active_key not in keys:
                self._exit_history_mode(trigger_refresh=False)
            else:
                index = keys.index(active_key)
                self.history_listbox.selection_set(index)
                self.history_listbox.see(index)

        self._refresh_history_controls_state()

    def _format_history_entry(self, snapshot: HistoricalSnapshot) -> str:
        local_dt = snapshot.captured_at.astimezone(self._timezone)
        tz_label = local_dt.tzname() or self._timezone_name
        timestamp = local_dt.strftime("%Y-%m-%d %H:%M")
        headline_label = "headline" if snapshot.headline_count == 1 else "headlines"
        return f"{timestamp} {tz_label} • {snapshot.headline_count} {headline_label}"

    def _format_history_tooltip(self, snapshot: HistoricalSnapshot) -> str:
        local_dt = snapshot.captured_at.astimezone(self._timezone)
        tz_label = local_dt.tzname() or self._timezone_name
        lines = [
            f"Captured: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_label}",
            f"Redis key: {snapshot.key}",
            f"Headlines: {snapshot.headline_count}",
        ]
        if snapshot.summary_count:
            lines.append(f"Summaries: {snapshot.summary_count}")
        ticker_preview = snapshot.cache.ticker_text or ""
        if ticker_preview:
            truncated = ticker_preview if len(ticker_preview) <= 120 else ticker_preview[:117].rstrip() + "…"
            lines.append(f"Ticker: {truncated}")
        return "\n".join(lines)

    def _on_history_select(self, _event: tk.Event) -> None:
        if self.history_listbox.cget("state") != tk.NORMAL:
            return
        self._activate_history_selection()

    def _activate_history_selection(
        self, _event: Optional[tk.Event] = None
    ) -> Optional[str]:
        if self.history_listbox.cget("state") != tk.NORMAL:
            return "break" if _event is not None else None
        selection = self.history_listbox.curselection()
        if not selection:
            return "break" if _event is not None else None
        index = selection[0]
        if index < 0 or index >= len(self._history_entries):
            return "break" if _event is not None else None
        snapshot = self._history_entries[index]
        self._apply_history_snapshot(snapshot)
        return "break" if _event is not None else None

    def _on_history_motion(self, event: tk.Event) -> None:
        if self.history_listbox.cget("state") != tk.NORMAL:
            self.history_listbox_hover.hide()
            return
        if not self._history_entries:
            self.history_listbox_hover.hide()
            return
        index = self.history_listbox.nearest(event.y)
        if index < 0 or index >= len(self._history_entries):
            self.history_listbox_hover.hide()
            return
        snapshot = self._history_entries[index]
        tooltip = self._format_history_tooltip(snapshot)
        self.history_listbox_hover.show(tooltip, event.x_root, event.y_root)

    def _capture_live_flow_state(self) -> LiveFlowState:
        listbox_view_top: Optional[float] = None
        try:
            view = self.listbox.yview()
        except Exception:
            view = None
        if view:
            listbox_view_top = float(view[0])

        selection_index = self._selected_line

        return LiveFlowState(
            next_refresh_time=self._next_refresh_time,
            auto_refresh_enabled=bool(self.auto_refresh_var.get()),
            background_watch_enabled=bool(self.background_watch_var.get()),
            background_watch_next_run=self._background_watch_next_run,
            pending_new_headlines=self._pending_new_headlines,
            last_reported_pending=self._last_reported_pending,
            background_candidate_keys=frozenset(self._background_candidate_keys),
            listbox_view_top=listbox_view_top,
            listbox_selection=selection_index,
        )

    def _apply_history_snapshot(self, snapshot: HistoricalSnapshot) -> None:
        self.history_listbox_hover.hide()
        self._ensure_options_visible()
        if not self._history_mode:
            raw_headlines = (
                list(self._raw_headlines) if self._raw_headlines else list(self.headlines)
            )
            self._last_live_payload = (
                raw_headlines,
                self._current_ticker_text,
                self._last_headline_from_cache,
            )
            self._last_live_flow_state = self._capture_live_flow_state()
        self._history_mode = True
        self._history_active_snapshot = snapshot
        self.exit_history_btn.config(state=tk.NORMAL)
        ticker_text = snapshot.cache.ticker_text or build_ticker_text(snapshot.cache.headlines)
        self.history_status_var.set(
            f"History mode: {self._format_history_entry(snapshot)}"
        )
        self._log_status(
            f"Viewing historical snapshot captured at {snapshot.captured_at.isoformat()}."
        )
        self._cancel_pending_refresh_jobs()
        self._next_refresh_time = None
        self.next_refresh_var.set("Next refresh: history view")
        self._update_content(
            headlines=list(snapshot.cache.headlines),
            ticker_text=ticker_text,
            from_cache=True,
            reschedule=False,
            log_status=False,
            update_tickers=False,
        )
        self._log_status(
            f"Loaded {snapshot.headline_count} cached headlines captured at {snapshot.captured_at.isoformat()}."
        )
        try:
            self._clear_listbox_selection()
            self.listbox.yview_moveto(0.0)
        except Exception:
            logger.debug("Unable to reset main listbox selection after history load.")

    def _restore_live_flow_state(self) -> tuple[bool, bool, bool]:
        snapshot = self._last_live_flow_state
        if snapshot is None:
            return False, False, False
        self._last_live_flow_state = None

        self._pending_new_headlines = snapshot.pending_new_headlines
        self._last_reported_pending = snapshot.last_reported_pending
        self._background_candidate_keys = set(snapshot.background_candidate_keys)
        self._update_background_watch_label()

        if snapshot.listbox_selection is not None:
            try:
                self._select_listbox_line(snapshot.listbox_selection)
                self.listbox.see(f"{snapshot.listbox_selection}.0")
            except Exception:
                logger.debug("Unable to restore listbox selection from live state.")
        if snapshot.listbox_view_top is not None:
            try:
                self.listbox.yview_moveto(snapshot.listbox_view_top)
            except Exception:
                logger.debug("Unable to restore listbox scroll position from live state.")

        auto_scheduled = False
        background_scheduled = False
        refresh_triggered = False
        auto_enabled_now = bool(self.auto_refresh_var.get())

        if not auto_enabled_now:
            self._schedule_auto_refresh()
            auto_scheduled = True
        elif snapshot.auto_refresh_enabled and snapshot.next_refresh_time is not None:
            remaining_ms = int(
                (snapshot.next_refresh_time - datetime.now()).total_seconds() * 1000
            )
            if remaining_ms <= 0:
                self.refresh_headlines(force_refresh=True)
                refresh_triggered = True
            else:
                self._schedule_auto_refresh_with_delay(remaining_ms)
            auto_scheduled = True
        else:
            self._schedule_auto_refresh()
            auto_scheduled = True

        background_enabled_now = bool(self.background_watch_var.get())
        if not background_enabled_now:
            self._cancel_background_watch()
            self._background_watch_next_run = None
            self._update_background_watch_label()
            background_scheduled = True
        elif (
            snapshot.background_watch_enabled
            and snapshot.background_watch_next_run is not None
        ):
            delay_ms = int(
                (snapshot.background_watch_next_run - datetime.now()).total_seconds()
                * 1000
            )
            if delay_ms <= 0:
                self._schedule_background_watch_with_delay(0)
            else:
                self._schedule_background_watch_with_delay(delay_ms)
            background_scheduled = True
        else:
            self._schedule_background_watch()
            background_scheduled = True

        return auto_scheduled, background_scheduled, refresh_triggered

    def _exit_history_mode(self, *, trigger_refresh: bool = True) -> None:
        if not self._history_mode:
            return
        self._history_mode = False
        self._history_active_snapshot = None
        self.exit_history_btn.config(state=tk.DISABLED)
        self.history_listbox.selection_clear(0, tk.END)
        self.history_listbox_hover.hide()
        if self._history_entries:
            self.history_status_var.set(
                f"{len(self._history_entries)} snapshots loaded (newest first). Select to view."
            )
        else:
            self.history_status_var.set(
                "History mode off — refresh to browse cached snapshots."
            )

        restored = False
        if self._last_live_payload:
            raw_headlines, ticker_text, from_cache = self._last_live_payload
            self._last_live_payload = None
            self._update_content(
                headlines=list(raw_headlines),
                ticker_text=ticker_text,
                from_cache=from_cache,
                reschedule=False,
                log_status=False,
                update_tickers=False,
            )
            restored = True

        auto_restored, background_restored, refresh_triggered = self._restore_live_flow_state()

        if not restored and trigger_refresh and not refresh_triggered:
            self.refresh_headlines(force_refresh=False)

        if not restored:
            self._restore_live_tickers()
        if not auto_restored:
            self._schedule_auto_refresh()
        if not background_restored:
            self._schedule_background_watch(immediate=True)
        self._refresh_history_controls_state()

    def _refresh_history_controls_state(self) -> None:
        history_enabled = bool(self.historical_cache_var.get())
        redis_enabled = bool(REDIS_URL)
        can_refresh = history_enabled and redis_enabled
        try:
            self.history_reload_btn.config(state=tk.NORMAL if can_refresh else tk.DISABLED)
        except Exception:
            logger.debug("Unable to update history reload button state.")

        if not can_refresh:
            self._exit_history_mode(trigger_refresh=False)
            placeholder = (
                "History unavailable — Redis disabled."
                if not redis_enabled
                else "History disabled. Enable the 24h history toggle to collect snapshots."
            )
            self.history_listbox.configure(state=tk.DISABLED)
            self.history_listbox.delete(0, tk.END)
            self.history_listbox.insert(tk.END, placeholder)
            self.history_status_var.set(placeholder)
            return

        if self._history_entries:
            if not self._history_mode:
                self.history_status_var.set(
                    f"{len(self._history_entries)} snapshots loaded (newest first). Select to view."
                )
            self.history_listbox.configure(state=tk.NORMAL)
        else:
            self.history_listbox.configure(state=tk.DISABLED)
            self.history_listbox.delete(0, tk.END)
            self.history_listbox.insert(
                tk.END,
                "History snapshots appear here when loaded.",
            )
            if not self._history_mode:
                self.history_status_var.set(
                    "History mode off — refresh to browse cached snapshots."
                )

    def open_heatmap(self) -> None:
        """Open or refresh the keyword heatmap window."""

        if self._heatmap_window and self._heatmap_window.winfo_exists():
            self._heatmap_window.update_data(self.headlines)
            self._heatmap_window.deiconify()
            self._heatmap_window.lift()
            return

        try:
            self._heatmap_window = KeywordHeatmapWindow(
                self,
                self.headlines,
                on_close=self._on_heatmap_closed,
            )
        except Exception:
            self._heatmap_window = None
            logger.exception("Failed to open keyword heatmap window.")
            self._log_status("Unable to open keyword heatmap window.", logging.ERROR)

    def _on_heatmap_closed(self) -> None:
        self._heatmap_window = None

    def _show_info_window(self) -> None:
        if self._info_window and self._info_window.winfo_exists():
            self._info_window.deiconify()
            self._info_window.lift()
            self._info_window.focus_force()
            return

        system_rows = self._build_system_rows()
        try:
            self._info_window = AppInfoWindow(
                self,
                metadata=APP_METADATA,
                system_rows=system_rows,
                on_close=self._on_info_window_closed,
            )
        except Exception:
            self._info_window = None
            logger.exception("Failed to open application info window.")
            self._log_status("Unable to open info window.", logging.ERROR)

    def _on_info_window_closed(self) -> None:
        self._info_window = None

    def _build_system_rows(self) -> List[tuple[str, str]]:
        system_name_raw = platform.system()
        os_name = system_name_raw.strip() if system_name_raw else ""

        release_raw = platform.release()
        os_release = release_raw.strip() if release_raw else ""

        version_raw = platform.version()
        os_version = version_raw.strip() if version_raw else ""

        os_summary_parts = [part for part in (os_name, os_release) if part]
        os_summary = " ".join(os_summary_parts) or "Unknown OS"
        if os_version:
            os_summary = f"{os_summary} ({os_version})"

        python_impl_raw = platform.python_implementation()
        python_impl = python_impl_raw.strip() if python_impl_raw else "Python"
        python_version_raw = platform.python_version()
        python_version = python_version_raw.strip() if python_version_raw else ""

        machine_raw = platform.machine()
        machine = machine_raw.strip() if machine_raw else ""

        processor_raw = platform.processor()
        processor = processor_raw.strip() if processor_raw else ""

        rows: List[tuple[str, str]] = [("Operating system", os_summary)]
        if machine:
            rows.append(("Machine", machine))
        if processor and processor.lower() != "unknown":
            rows.append(("Processor", processor))
        rows.append(("Python", f"{python_impl} {python_version}".strip()))
        rows.append(("Settings file", str(SETTINGS_PATH)))
        return rows

    def _filtered_entries(self) -> List[tuple[int, Headline]]:
        results: List[tuple[int, Headline]] = []
        for index, headline in enumerate(self.headlines):
            if self._matches_filters(headline):
                results.append((index, headline))
        return results

    def _matches_filters(self, headline: Headline) -> bool:
        section_filter = (self.section_filter_var.get() or "").strip()
        if section_filter and section_filter != "All sections":
            section_value = (
                headline.section.strip()
                if isinstance(headline.section, str)
                else ""
            )
            if section_value != section_filter:
                return False

        query = (self.search_var.get() or "").strip().lower()
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

    def _filters_active(self) -> bool:
        if (self.search_var.get() or "").strip():
            return True
        section_filter = (self.section_filter_var.get() or "").strip()
        return bool(section_filter and section_filter != "All sections")

    def _refresh_section_filter_menu(self, headlines: Sequence[Headline]) -> None:
        sections = {
            headline.section.strip()
            for headline in headlines
            if isinstance(headline.section, str) and headline.section.strip()
        }
        options = ["All sections", *sorted(sections)]
        if options == self._section_filter_options:
            return

        self._section_filter_options = options
        menu = self.section_filter_menu["menu"]
        menu.delete(0, "end")
        for option in options:
            menu.add_command(
                label=option,
                command=lambda value=option: self.section_filter_var.set(value),
            )

        if self.section_filter_var.get() not in options:
            self._suppress_section_filter_callback = True
            self.section_filter_var.set("All sections")
            self._suppress_section_filter_callback = False

    def _clear_search(self, event: Optional[tk.Event] = None) -> Optional[str]:
        if self.search_var.get():
            self.search_var.set("")
        if event is not None:
            return "break"
        return None

    def _on_search_change(self, *_args: object) -> None:
        if getattr(self, "_loading_settings", False):
            return
        self._render_filtered_headlines()

    def _on_section_filter_change(self, *_args: object) -> None:
        if getattr(self, "_loading_settings", False):
            return
        if getattr(self, "_suppress_section_filter_callback", False):
            return
        self._render_filtered_headlines()

    def _handle_fetch_error(self, exc: Exception) -> None:
        self.headlines = []
        self._clear_headline_list()
        self._cancel_relative_age_refresh()
        self.ticker.set_text("Unable to fetch AI headlines right now.")
        self.full_ticker.set_text("Unable to fetch AI headlines right now.")
        self._current_ticker_text = "Unable to fetch AI headlines right now."
        self._last_headline_from_cache = False
        self._live_ticker_items = []
        self._live_full_ticker_items = []
        self._log_status(f"Fetch failed: {exc}", level=logging.ERROR)
        logger.error("Headline refresh failed: %s", exc)
        self._update_redis_meter()
        self._pending_new_headlines = 0
        self._last_reported_pending = 0
        self._background_candidate_keys.clear()
        self._update_background_watch_label()
        self._schedule_auto_refresh()

    def _apply_speed(self, *_args: object) -> None:
        value = self.ticker_speed_var.get()
        clamped = max(1, min(20, int(value)))
        if clamped != value:
            self.ticker_speed_var.set(clamped)
        self.ticker.set_speed(clamped)
        self.settings["ticker_speed"] = clamped
        self._save_settings()

    def _toggle_logs(self) -> None:
        if self.log_visible:
            self.log_frame.pack_forget()
            self.log_visible = False
            self.toggle_logs_btn.config(text="Show Logs")
        else:
            self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            self.log_visible = True
            self.toggle_logs_btn.config(text="Hide Logs")
            self._flush_log_buffer()
        self.settings["log_visible"] = self.log_visible
        self._save_settings()

    def _toggle_options_panel(self) -> None:
        self._set_options_visibility(not self._options_visible)

    def _set_options_visibility(self, visible: bool, *, persist: bool = True) -> None:
        self._options_visible = bool(visible)
        if visible:
            if not self.options_container.winfo_ismapped():
                self.options_container.pack(fill="x", padx=10, pady=(0, 10))
            self.options_toggle_btn.config(text="Hide Options")
        else:
            self.options_container.pack_forget()
            self.options_toggle_btn.config(text="Show Options")
        if persist:
            self.settings["options_visible"] = self._options_visible
            self._save_settings()
        self._update_status_summary()

    def _ensure_options_visible(self) -> None:
        if not self._options_visible:
            self._set_options_visibility(True, persist=False)

    def _update_status_summary(self) -> None:
        if not hasattr(self, "status_summary_label"):
            return
        if self._options_visible:
            if self.status_summary_label.winfo_ismapped():
                self.status_summary_label.pack_forget()
            self.status_summary_var.set("")
            return
        parts: List[str] = []
        if bool(self.background_watch_var.get()):
            parts.append(self.new_headlines_var.get())
        parts.append(self.last_refresh_var.get())
        if bool(self.auto_refresh_var.get()):
            parts.append(self.next_refresh_var.get())
        text = " | ".join(part for part in parts if part)
        if not text:
            text = "Options hidden"
        self.status_summary_var.set(text)
        if not self.status_summary_label.winfo_ismapped():
            self.status_summary_label.pack(side="right", padx=(10, 0))

    def _update_heatmap_button_state(self) -> None:
        if not hasattr(self, "heatmap_btn"):
            return
        state = tk.NORMAL if has_highlight_pattern() else tk.DISABLED
        try:
            self.heatmap_btn.config(state=state)
        except Exception:  # pragma: no cover - Tk reconfigure issue
            logger.debug("Unable to update heatmap button state.")
        if state == tk.DISABLED and self._heatmap_window and self._heatmap_window.winfo_exists():
            try:
                self._heatmap_window.destroy()
            finally:
                self._heatmap_window = None

    def _refresh_views_for_highlight_update(self) -> None:
        if not hasattr(self, "_raw_headlines"):
            return
        self._render_filtered_headlines(
            reschedule=False,
            log_status=False,
            update_tickers=False,
        )
        if self._heatmap_window and self._heatmap_window.winfo_exists():
            if not has_highlight_pattern():
                try:
                    self._heatmap_window.destroy()
                finally:
                    self._heatmap_window = None
            else:
                self._heatmap_window.update_data(self.headlines)
        self._update_status_summary()

    def _update_highlight_keywords_setting(
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
        if hasattr(self, "highlight_keywords_var"):
            self.highlight_keywords_var.set(candidate)
        self.settings["highlight_keywords"] = candidate
        apply_highlight_keywords(parsed)
        self._update_heatmap_button_state()
        if refresh_views:
            self._refresh_views_for_highlight_update()
            if show_feedback:
                if candidate:
                    self._log_status("Highlight keywords updated from settings.")
                else:
                    self._log_status("Highlight keywords reset to defaults.")
        if persist:
            self._save_settings()

    def apply_highlight_keywords_from_var(self, *, show_feedback: bool) -> None:
        value = self.highlight_keywords_var.get() if hasattr(self, "highlight_keywords_var") else ""
        self._update_highlight_keywords_setting(
            value,
            refresh_views=True,
            persist=True,
            show_feedback=show_feedback,
        )

    def _on_highlight_keywords_return(self, *_args: object) -> str:
        self.apply_highlight_keywords_from_var(show_feedback=True)
        return "break"

    def _on_highlight_keywords_button(self) -> None:
        self.apply_highlight_keywords_from_var(show_feedback=True)

    def _sanitize_env_value(self, name: str, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if _SENSITIVE_ENV_PATTERN.search(name) or any(
            token in name for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")
        ):
            return "***" if value else None
        if len(value) > 80:
            return value[:77] + "…"
        return value

    def _log_startup_report(self) -> None:
        logger.info("AI News app initialised; settings file: %s", SETTINGS_PATH)
        env_overrides = {
            "NEWS_SUMMARY_TIMEOUT": os.getenv("NEWS_SUMMARY_TIMEOUT"),
            "NEWS_TICKER_TIMEOUT": os.getenv("NEWS_TICKER_TIMEOUT"),
            "NEWS_CACHE_KEY": os.getenv("NEWS_CACHE_KEY"),
            "NEWS_CACHE_TTL": os.getenv("NEWS_CACHE_TTL"),
            "NEWS_HISTORY_PREFIX": os.getenv("NEWS_HISTORY_PREFIX"),
            "NEWS_HISTORY_TTL": os.getenv("NEWS_HISTORY_TTL"),
            "REDIS_URL": os.getenv("REDIS_URL"),
            "NEWS_APP_SETTINGS": os.getenv("NEWS_APP_SETTINGS"),
            "NEWS_SUMMARY_MODEL": os.getenv("NEWS_SUMMARY_MODEL"),
            "NEWS_SUMMARY_PROVIDER": os.getenv("NEWS_SUMMARY_PROVIDER"),
            "NEWS_SUMMARY_API_BASE": os.getenv("NEWS_SUMMARY_API_BASE"),
            "NEWS_SUMMARY_API_KEY": os.getenv("NEWS_SUMMARY_API_KEY"),
            "NEWS_SUMMARY_AZURE_DEPLOYMENT": os.getenv("NEWS_SUMMARY_AZURE_DEPLOYMENT"),
            "NEWS_SUMMARY_AZURE_API_VERSION": os.getenv("NEWS_SUMMARY_AZURE_API_VERSION"),
            "NEWS_SUMMARY_AZURE_AD_TOKEN": os.getenv("NEWS_SUMMARY_AZURE_AD_TOKEN"),
            "LITELLM_MODEL": os.getenv("LITELLM_MODEL"),
            "LITELLM_PROVIDER": os.getenv("LITELLM_PROVIDER"),
            "LITELLM_API_BASE": os.getenv("LITELLM_API_BASE"),
            "LITELLM_API_KEY": os.getenv("LITELLM_API_KEY"),
            "AZURE_OPENAI_DEPLOYMENT": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            "AZURE_OPENAI_API_BASE": os.getenv("AZURE_OPENAI_API_BASE"),
            "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION"),
            "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
            "AZURE_OPENAI_AD_TOKEN": os.getenv("AZURE_OPENAI_AD_TOKEN"),
        }
        safe_env = {
            name: sanitized
            for name, value in env_overrides.items()
            if (sanitized := self._sanitize_env_value(name, value)) is not None
        }
        logger.info(
            "Startup settings: %s",
            {
                "ticker_speed": self.settings.get("ticker_speed"),
                "color_profile": self.settings.get("color_profile"),
                "window_geometry": self.settings.get("window_geometry"),
                "log_visible": self.settings.get("log_visible"),
                "debug_mode": self.settings.get("debug_mode"),
                "litellm_debug": self.settings.get("litellm_debug"),
                "historical_cache_enabled": self.settings.get(
                    "historical_cache_enabled"
                ),
                "auto_refresh_enabled": self.settings.get("auto_refresh_enabled"),
                "auto_refresh_minutes": self.settings.get("auto_refresh_minutes"),
                "redis_enabled": bool(REDIS_URL),
            },
        )
        if safe_env:
            logger.info("Startup environment overrides: %s", safe_env)

    def _log_status(self, message: str, level: int = logging.INFO) -> None:
        self._latest_status = message
        logger.log(level, message)
        if self.log_visible:
            self._flush_log_buffer()

    def _on_root_configure(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        if not getattr(self, "_geometry_tracking_ready", False):
            return
        if getattr(self, "_loading_settings", False):
            return
        if str(self.state()) != "normal":
            return
        geometry = self.geometry()
        if not geometry:
            return
        if geometry == self._last_geometry:
            return
        self._last_geometry = geometry
        self.settings["window_geometry"] = geometry

    def _remember_window_geometry(self) -> None:
        geometry: Optional[str]
        if str(self.state()) == "normal":
            geometry = self.geometry()
        else:
            geometry = self._last_geometry or self.geometry()
        if geometry:
            self._last_geometry = geometry
            self.settings["window_geometry"] = geometry

    def _on_close(self) -> None:
        self._cancel_relative_age_refresh()
        self._cancel_background_watch()
        self._remember_window_geometry()
        self._save_settings()
        self.destroy()

    def _toggle_debug_mode(self) -> None:
        debug_enabled = bool(self.debug_var.get())
        self.settings["debug_mode"] = debug_enabled
        self._update_handler_level()
        self._save_settings()

    def _toggle_litellm_debug(self) -> None:
        enabled = bool(self.litellm_debug_var.get())
        self.settings["litellm_debug"] = enabled
        configure_litellm_debug(enabled)
        logger.info("LiteLLM debug %s", "enabled" if enabled else "disabled")
        self._save_settings()

    def _toggle_historical_cache(self) -> None:
        enabled = bool(self.historical_cache_var.get())
        self.settings["historical_cache_enabled"] = enabled
        set_historical_cache_enabled(enabled)
        logger.info(
            "24h historical cache %s", "enabled" if enabled else "disabled"
        )
        self._save_settings()
        self._refresh_history_controls_state()

    def _toggle_auto_refresh(self) -> None:
        enabled = bool(self.auto_refresh_var.get())
        self.settings["auto_refresh_enabled"] = enabled
        logger.info("Auto refresh %s", "enabled" if enabled else "disabled")
        self._save_settings()
        self._schedule_auto_refresh()
        self._update_status_summary()

    def _toggle_background_watch(self) -> None:
        enabled = bool(self.background_watch_var.get())
        self.settings["background_watch_enabled"] = enabled
        if not enabled:
            self._pending_new_headlines = 0
            self._last_reported_pending = 0
            self._background_candidate_keys.clear()
        logger.info("Background watch %s", "enabled" if enabled else "disabled")
        self._update_background_watch_label()
        self._save_settings()
        self._schedule_background_watch(immediate=enabled)
        if enabled:
            self._maybe_auto_refresh_for_pending()
        self._update_status_summary()

    def _auto_refresh_interval_ms(self) -> int:
        try:
            minutes = int(self.auto_refresh_minutes_var.get())
        except (ValueError, tk.TclError):
            minutes = DEFAULT_SETTINGS["auto_refresh_minutes"]
        minutes = max(1, min(180, minutes))
        self.auto_refresh_minutes_var.set(minutes)
        return minutes * 60_000

    def _update_auto_refresh_minutes(self, *_args: object) -> None:
        self._auto_refresh_interval_ms()
        self.settings["auto_refresh_minutes"] = int(self.auto_refresh_minutes_var.get())
        self._save_settings()
        self._schedule_auto_refresh()

    def _cancel_pending_refresh_jobs(self) -> None:
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
            self._refresh_job = None
        if self._countdown_job is not None:
            try:
                self.after_cancel(self._countdown_job)
            except tk.TclError:
                pass
            self._countdown_job = None

    def _schedule_auto_refresh(self) -> None:
        self._cancel_pending_refresh_jobs()
        if self._history_mode:
            self._next_refresh_time = None
            self.next_refresh_var.set("Next refresh: history view")
            return
        auto_enabled = bool(self.auto_refresh_var.get())
        if not auto_enabled:
            self._next_refresh_time = None
            self.next_refresh_var.set("Next refresh: paused")
        else:
            interval_ms = self._auto_refresh_interval_ms()
            self.refresh_interval = interval_ms
            self._next_refresh_time = datetime.now() + timedelta(milliseconds=interval_ms)
            self._refresh_job = self.after(interval_ms, self._auto_refresh_trigger)
        self._start_refresh_countdown()
        self._update_status_summary()

    def _schedule_auto_refresh_with_delay(self, delay_ms: int) -> None:
        delay = max(0, int(delay_ms))
        self._cancel_pending_refresh_jobs()
        if self._history_mode:
            self._next_refresh_time = None
            self.next_refresh_var.set("Next refresh: history view")
            return
        if not bool(self.auto_refresh_var.get()):
            self._next_refresh_time = None
            self.next_refresh_var.set("Next refresh: paused")
            self._start_refresh_countdown()
            return
        interval_ms = self._auto_refresh_interval_ms()
        self.refresh_interval = interval_ms
        if delay == 0:
            self._next_refresh_time = datetime.now()
            self._refresh_job = self.after_idle(self._auto_refresh_trigger)
        else:
            self._next_refresh_time = datetime.now() + timedelta(milliseconds=delay)
            self._refresh_job = self.after(delay, self._auto_refresh_trigger)
        self._start_refresh_countdown()
        self._update_status_summary()

    def _auto_refresh_trigger(self) -> None:
        self._refresh_job = None
        self.refresh_headlines(force_refresh=True)

    def _start_refresh_countdown(self) -> None:
        if self._countdown_job is not None:
            try:
                self.after_cancel(self._countdown_job)
            except tk.TclError:
                pass
        self._countdown_job = self.after(0, self._tick_refresh_countdown)

    def _update_last_refresh_label(self) -> None:
        if self._last_refresh_time is None:
            self.last_refresh_var.set("Last refresh: pending")
            return

        elapsed = datetime.now() - self._last_refresh_time
        elapsed_seconds = max(0, int(elapsed.total_seconds()))
        if elapsed_seconds < 60:
            label = f"{elapsed_seconds}s ago"
        elif elapsed_seconds < 3600:
            minutes, seconds = divmod(elapsed_seconds, 60)
            label = f"{minutes}m {seconds:02d}s ago"
        else:
            hours, remainder = divmod(elapsed_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            label = f"{hours}h {minutes:02d}m {seconds:02d}s ago"

        self.last_refresh_var.set(f"Last refresh: {label}")
        self._update_status_summary()

    def _tick_refresh_countdown(self) -> None:
        auto_enabled = bool(self.auto_refresh_var.get())
        if self._history_mode:
            self.next_refresh_var.set("Next refresh: history view")
        elif not auto_enabled or self._next_refresh_time is None:
            self.next_refresh_var.set("Next refresh: paused")
        else:
            remaining = int((self._next_refresh_time - datetime.now()).total_seconds())
            if remaining <= 0:
                self.next_refresh_var.set("Next refresh: 00:00")
            else:
                minutes, seconds = divmod(remaining, 60)
                self.next_refresh_var.set(f"Next refresh: {minutes:02d}:{seconds:02d}")

        self._update_last_refresh_label()
        self._countdown_job = self.after(1000, self._tick_refresh_countdown)

    def _schedule_background_watch(self, *, immediate: bool = False) -> None:
        self._cancel_background_watch()
        if not bool(self.background_watch_var.get()):
            self._background_watch_next_run = None
            return
        delay = BACKGROUND_WATCH_INITIAL_DELAY_MS if immediate else BACKGROUND_WATCH_INTERVAL_MS
        if delay <= 0:
            delay = BACKGROUND_WATCH_INTERVAL_MS
        self._background_watch_next_run = datetime.now() + timedelta(milliseconds=delay)
        self._background_watch_job = self.after(delay, self._background_watch_trigger)

    def _schedule_background_watch_with_delay(self, delay_ms: int) -> None:
        self._cancel_background_watch()
        if not bool(self.background_watch_var.get()):
            self._background_watch_next_run = None
            return
        delay = max(0, int(delay_ms))
        if delay == 0:
            self._background_watch_next_run = datetime.now()
            self._background_watch_job = self.after_idle(self._background_watch_trigger)
        else:
            self._background_watch_next_run = datetime.now() + timedelta(milliseconds=delay)
            self._background_watch_job = self.after(delay, self._background_watch_trigger)

    def _cancel_background_watch(self) -> None:
        if self._background_watch_job is not None:
            try:
                self.after_cancel(self._background_watch_job)
            except tk.TclError:
                pass
            self._background_watch_job = None
        self._background_watch_next_run = None

    def _background_watch_trigger(self) -> None:
        self._background_watch_next_run = None
        self._background_watch_job = None
        if not bool(self.background_watch_var.get()):
            return
        if self._background_watch_running:
            self._schedule_background_watch()
            return
        if self._history_mode:
            self._schedule_background_watch()
            return
        self._background_watch_running = True
        threading.Thread(target=self._background_watch_worker, daemon=True).start()

    def _background_watch_worker(self) -> None:
        try:
            headlines, _from_cache, _ticker = fetch_headlines(force_refresh=True)
        except Exception as exc:  # pragma: no cover - network failures
            logger.debug("Background watch fetch failed: %s", exc)
            self.after(0, lambda: self._handle_background_watch_failure())
            return
        self.after(0, lambda: self._handle_background_watch_result(headlines))

    def _handle_background_watch_failure(self) -> None:
        self._background_watch_running = False
        if bool(self.background_watch_var.get()):
            self._schedule_background_watch()

    def _handle_background_watch_result(self, headlines: List[Headline]) -> None:
        self._background_watch_running = False
        if not bool(self.background_watch_var.get()):
            self._pending_new_headlines = 0
            self._last_reported_pending = 0
            self._update_background_watch_label()
            return
        if self._history_mode:
            self._schedule_background_watch()
            return
        filtered = self._filter_headlines(headlines)
        current_keys = {
            self._headline_key(headline)
            for _, headline in self._filtered_entries()
        }
        candidate_keys = {
            self._headline_key(headline)
            for headline in filtered
            if self._matches_filters(headline)
        }
        self._background_candidate_keys = candidate_keys
        pending = len(candidate_keys.difference(current_keys))
        self._pending_new_headlines = pending
        if pending != self._last_reported_pending:
            if pending > 0:
                logger.info(
                    "Background watch detected %s unseen headline(s).", pending
                )
            elif self._last_reported_pending > 0:
                logger.info("Background watch count cleared after refresh.")
            self._last_reported_pending = pending
        self._update_background_watch_label()
        self._maybe_auto_refresh_for_pending()
        self._schedule_background_watch()

    def _update_background_watch_label(self) -> None:
        if not hasattr(self, "new_headlines_var"):
            return
        enabled = bool(self.background_watch_var.get())
        if not enabled:
            self.new_headlines_var.set("Background watch: off")
            if hasattr(self, "new_headlines_label"):
                self.new_headlines_label.config(fg="lightgray")
            return
        count = max(0, int(self._pending_new_headlines))
        if count > 0:
            self.new_headlines_var.set(f"New headlines pending: {count}")
            if hasattr(self, "new_headlines_label"):
                self.new_headlines_label.config(fg="#FFD54F")
        else:
            self.new_headlines_var.set("New headlines pending: 0")
            if hasattr(self, "new_headlines_label"):
                self.new_headlines_label.config(fg="#89CFF0")
        self._update_status_summary()

    @staticmethod
    def _headline_key(headline: Headline) -> tuple[str, str]:
        title = headline.title.strip().lower() if isinstance(headline.title, str) else ""
        url = headline.url.strip() if isinstance(headline.url, str) else ""
        return title, url

    def _coerce_background_watch_threshold(self, value: Any) -> int:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            numeric = DEFAULT_SETTINGS["background_watch_refresh_threshold"]
        return max(1, min(999, numeric))

    def _apply_background_watch_threshold(self, *_args: object) -> None:
        threshold = self._coerce_background_watch_threshold(
            self.background_watch_threshold_var.get()
        )
        if threshold != self.background_watch_threshold_var.get():
            self.background_watch_threshold_var.set(threshold)
        if threshold == self._background_refresh_threshold:
            return
        self._background_refresh_threshold = threshold
        self.settings["background_watch_refresh_threshold"] = threshold
        self._save_settings()
        self._maybe_auto_refresh_for_pending()

    def _recompute_background_pending(self) -> None:
        if not bool(self.background_watch_var.get()):
            return
        if not self._background_candidate_keys:
            return
        current_keys = {
            self._headline_key(headline)
            for _, headline in self._filtered_entries()
        }
        pending = len(self._background_candidate_keys.difference(current_keys))
        if pending == self._pending_new_headlines:
            return
        self._pending_new_headlines = pending
        self._last_reported_pending = pending
        self._update_background_watch_label()
        self._maybe_auto_refresh_for_pending()

    def _maybe_auto_refresh_for_pending(self) -> None:
        if not bool(self.background_watch_var.get()):
            return
        if self._history_mode:
            return
        threshold = max(1, int(self._background_refresh_threshold))
        if self._pending_new_headlines < threshold:
            return
        if getattr(self, "_background_watch_running", False):
            return
        if self._refresh_job is not None:
            self._cancel_pending_refresh_jobs()
            self._next_refresh_time = None

        self._log_status(
            f"Auto-refreshing for {self._pending_new_headlines} unseen headline(s)."
        )
        logger.info(
            "Triggering auto refresh after reaching unseen headline threshold (%s).",
            self._pending_new_headlines,
        )
        self._pending_new_headlines = 0
        self._last_reported_pending = 0
        self._background_candidate_keys.clear()
        self._update_background_watch_label()
        self.refresh_headlines(force_refresh=True)

    def _update_handler_level(self) -> None:
        if bool(self.debug_var.get()):
            self.log_handler.setLevel(logging.DEBUG)
            if hasattr(self, "console_handler"):
                self.console_handler.setLevel(logging.DEBUG)
            logger.info("Debug logging enabled.")
        else:
            self.log_handler.setLevel(logging.INFO)
            if hasattr(self, "console_handler"):
                self.console_handler.setLevel(logging.INFO)
            logger.info("Debug logging disabled; showing INFO and above.")

    def _handle_log_record(self, level: int, message: str) -> None:
        self.log_buffer.append((level, message))
        self.after(0, self._flush_log_buffer)

    def _flush_log_buffer(self) -> None:
        while self.log_buffer:
            _level, msg = self.log_buffer.popleft()
            self._append_log_line(msg)

    def _append_log_line(self, message: str) -> None:
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > 500:
            self.log_text.delete("1.0", f"{line_count - 500}.0")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _apply_settings_from_store(self) -> None:
        highlight_value = self.settings.get("highlight_keywords", "")
        if not isinstance(highlight_value, str):
            highlight_value = ""
        self._update_highlight_keywords_setting(
            highlight_value,
            refresh_views=True,
            persist=False,
            show_feedback=False,
        )

        speed = int(self.settings.get("ticker_speed", DEFAULT_SETTINGS["ticker_speed"]))
        self.ticker_speed_var.set(speed)
        self.ticker.set_speed(speed)
        self.settings["ticker_speed"] = speed

        timezone_value = str(self.settings.get("timezone", DEFAULT_TIMEZONE))
        self._apply_timezone_selection(timezone_value, persist=False)

        profile = self.settings.get(
            "color_profile", DEFAULT_SETTINGS["color_profile"]
        )
        if profile == CUSTOM_PROFILE_NAME:
            background = self.settings.get(
                "custom_background", DEFAULT_SETTINGS["custom_background"]
            )
            text_color = self.settings.get(
                "custom_text", DEFAULT_SETTINGS["custom_text"]
            )
            COLOR_PROFILES[CUSTOM_PROFILE_NAME] = {
                "background": background,
                "text": text_color,
                "hover": _derive_hover_color(text_color),
            }
            self.color_profile_var.set(CUSTOM_PROFILE_NAME)
            self.ticker_bg_var.set(background)
            self.ticker_fg_var.set(text_color)
            self.ticker.set_colors(background=background, text=text_color)
        elif profile in COLOR_PROFILES:
            self.color_profile_var.set(profile)
            self._apply_color_profile(profile)
            profile_colors = COLOR_PROFILES[profile]
            self.ticker_bg_var.set(profile_colors["background"])
            self.ticker_fg_var.set(profile_colors["text"])
        else:
            self.color_profile_var.set(DEFAULT_COLOR_PROFILE_NAME)
            self._apply_color_profile(DEFAULT_COLOR_PROFILE_NAME)
            profile_colors = COLOR_PROFILES[DEFAULT_COLOR_PROFILE_NAME]
            self.ticker_bg_var.set(profile_colors["background"])
            self.ticker_fg_var.set(profile_colors["text"])

        desired_log = bool(
            self.settings.get("log_visible", DEFAULT_SETTINGS["log_visible"])
        )
        if desired_log and not self.log_visible:
            self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            self.log_visible = True
            self.toggle_logs_btn.config(text="Hide Logs")
            self._flush_log_buffer()
        elif not desired_log and self.log_visible:
            self.log_frame.pack_forget()
            self.log_visible = False
            self.toggle_logs_btn.config(text="Show Logs")
        debug_enabled = bool(
            self.settings.get("debug_mode", DEFAULT_SETTINGS["debug_mode"])
        )
        self.debug_var.set(debug_enabled)
        self._update_handler_level()
        litellm_debug_enabled = bool(
            self.settings.get("litellm_debug", DEFAULT_SETTINGS["litellm_debug"])
        )
        self.litellm_debug_var.set(litellm_debug_enabled)
        configure_litellm_debug(litellm_debug_enabled)
        self.settings["litellm_debug"] = litellm_debug_enabled
        historical_enabled = bool(
            self.settings.get(
                "historical_cache_enabled",
                DEFAULT_SETTINGS["historical_cache_enabled"],
            )
        )
        self.historical_cache_var.set(historical_enabled)
        self.settings["historical_cache_enabled"] = historical_enabled
        set_historical_cache_enabled(historical_enabled)
        auto_enabled = bool(
            self.settings.get(
                "auto_refresh_enabled", DEFAULT_SETTINGS["auto_refresh_enabled"]
            )
        )
        minutes = max(
            1,
            int(
                self.settings.get(
                    "auto_refresh_minutes",
                    DEFAULT_SETTINGS["auto_refresh_minutes"],
                )
            ),
        )
        self.auto_refresh_var.set(auto_enabled)
        self.auto_refresh_minutes_var.set(minutes)
        self.settings["auto_refresh_enabled"] = auto_enabled
        self.settings["auto_refresh_minutes"] = minutes
        background_watch_enabled = bool(
            self.settings.get(
                "background_watch_enabled",
                DEFAULT_SETTINGS["background_watch_enabled"],
            )
        )
        self.background_watch_var.set(background_watch_enabled)
        self.settings["background_watch_enabled"] = background_watch_enabled
        threshold = self._coerce_background_watch_threshold(
            self.settings.get(
                "background_watch_refresh_threshold",
                DEFAULT_SETTINGS["background_watch_refresh_threshold"],
            )
        )
        self._background_refresh_threshold = threshold
        self.background_watch_threshold_var.set(threshold)
        self.settings["background_watch_refresh_threshold"] = threshold
        if not background_watch_enabled:
            self._pending_new_headlines = 0
            self._last_reported_pending = 0
        self._update_background_watch_label()
        self._schedule_background_watch(immediate=background_watch_enabled)
        self.settings["color_profile"] = self.color_profile_var.get()
        self.settings["log_visible"] = self.log_visible
        self._refresh_profile_menu()
        self._set_options_visibility(
            bool(self.settings.get("options_visible", self._options_visible)),
            persist=False,
        )
        self._refresh_history_controls_state()
        self._update_status_summary()

    def _save_settings(self) -> None:
        if getattr(self, "_loading_settings", False):
            return
        save_settings(self.settings)

    def _reset_settings(self) -> None:
        if not messagebox.askyesno(
            "Reset Settings",
            "Reset all NewsNow Neon settings to their defaults?\n\n"
            "This clears saved preferences including highlight keywords, color profiles, refresh timers, and Redis options.",
            parent=self,
        ):
            return
        self.settings = DEFAULT_SETTINGS.copy()
        COLOR_PROFILES[CUSTOM_PROFILE_NAME] = {
            "background": self.settings["custom_background"],
            "text": self.settings["custom_text"],
            "hover": _derive_hover_color(self.settings["custom_text"]),
        }
        was_loading = getattr(self, "_loading_settings", False)
        self._loading_settings = True
        self._apply_settings_from_store()
        self._loading_settings = was_loading
        self.debug_var.set(self.settings["debug_mode"])
        self._update_handler_level()
        self.litellm_debug_var.set(self.settings["litellm_debug"])
        configure_litellm_debug(self.settings["litellm_debug"])
        self.historical_cache_var.set(self.settings["historical_cache_enabled"])
        set_historical_cache_enabled(self.settings["historical_cache_enabled"])
        self.auto_refresh_var.set(self.settings["auto_refresh_enabled"])
        self.auto_refresh_minutes_var.set(self.settings["auto_refresh_minutes"])
        self.background_watch_var.set(self.settings["background_watch_enabled"])
        self._background_refresh_threshold = self._coerce_background_watch_threshold(
            self.settings["background_watch_refresh_threshold"]
        )
        self.background_watch_threshold_var.set(self._background_refresh_threshold)
        self._pending_new_headlines = 0
        self._last_reported_pending = 0
        self._background_candidate_keys.clear()
        self._update_background_watch_label()
        self._save_settings()
        self._schedule_auto_refresh()
        self._schedule_background_watch(immediate=bool(self.background_watch_var.get()))
        self._log_status("Settings reset to defaults.")

    def _apply_color_profile(self, selected: Optional[str] = None) -> None:
        name = selected or self.color_profile_var.get()
        if name not in COLOR_PROFILES:
            return
        profile = COLOR_PROFILES[name]
        self.ticker.apply_color_profile(profile)
        self.full_ticker.apply_color_profile(profile)
        if hasattr(self, "ticker_bg_var"):
            self.ticker_bg_var.set(profile["background"])
            self.ticker_fg_var.set(profile["text"])
        self.settings["color_profile"] = name
        self._save_settings()

    def _choose_color(self, target: str) -> None:
        initial = (
            self.ticker_bg_var.get()
            if target == "background"
            else self.ticker_fg_var.get()
        )
        color = colorchooser.askcolor(initialcolor=initial)[1]
        if not color:
            return
        if target == "background":
            self.ticker_bg_var.set(color)
        else:
            self.ticker_fg_var.set(color)
        self._update_ticker_colors()
        self.color_profile_var.set(CUSTOM_PROFILE_NAME)

    def _update_ticker_colors(self) -> None:
        background = self.ticker_bg_var.get()
        text = self.ticker_fg_var.get()
        self.ticker.set_colors(background=background, text=text)
        hover_color = self.ticker.hover_color
        COLOR_PROFILES[CUSTOM_PROFILE_NAME] = {
            "background": background,
            "text": text,
            "hover": hover_color,
        }
        self.settings["custom_background"] = background
        self.settings["custom_text"] = text
        self.settings["color_profile"] = CUSTOM_PROFILE_NAME
        if not getattr(self, "_loading_settings", False):
            self.color_profile_var.set(CUSTOM_PROFILE_NAME)
        self._refresh_profile_menu()
        self._save_settings()

    def _refresh_profile_menu(self) -> None:
        options = _profile_name_options()
        menu = self.profile_menu["menu"]
        menu.delete(0, "end")
        for name in options:
            menu.add_command(
                label=name,
                command=lambda value=name: self._on_profile_selected(value),
            )

    def _refresh_timezone_menu(self) -> None:
        menu = self.timezone_menu["menu"]
        menu.delete(0, "end")
        # Maintain insertion order while avoiding duplicates.
        seen: set[str] = set()
        deduped_options: List[str] = []
        for option in self._timezone_options:
            if option not in seen:
                seen.add(option)
                deduped_options.append(option)
        self._timezone_options = deduped_options
        for option in self._timezone_options:
            menu.add_command(
                label=option,
                command=lambda value=option: self.timezone_var.set(value),
            )

    def _on_timezone_change(self, *_args: object) -> None:
        if self._suppress_timezone_callback:
            return
        persist = not getattr(self, "_loading_settings", False)
        self._apply_timezone_selection(self.timezone_var.get(), persist=persist)

    def _apply_timezone_selection(self, value: str, *, persist: bool) -> None:
        normalized, zone = _coerce_timezone(value)
        self._timezone_name = normalized
        self._timezone = zone
        if normalized not in self._timezone_options:
            self._timezone_options.append(normalized)
            self._refresh_timezone_menu()
        if self.timezone_var.get() != normalized:
            self._suppress_timezone_callback = True
            self.timezone_var.set(normalized)
            self._suppress_timezone_callback = False
        self.settings["timezone"] = normalized
        if persist and not getattr(self, "_loading_settings", False):
            self._save_settings()
        self._refresh_timezone_display()

    def _refresh_timezone_display(self) -> None:
        if not self.headlines:
            return
        ticker_text = self._current_ticker_text or build_ticker_text(self.headlines)
        self._update_content(
            headlines=self.headlines,
            ticker_text=ticker_text,
            from_cache=self._last_headline_from_cache,
            reschedule=False,
            log_status=False,
        )

    def _on_profile_selected(self, name: str) -> None:
        self.color_profile_var.set(name)
        self._apply_color_profile(name)

    def refresh_color_profiles(self) -> None:
        """Expose profile menu refresh for future dynamic profile additions."""
        self._refresh_profile_menu()

    def open_selected_headline(self, event: tk.Event) -> None:
        line: Optional[int] = None
        if event is not None and event.x is not None and event.y is not None:
            try:
                idx = self.listbox.index(f"@{event.x},{event.y}")
                line = int(float(idx.split(".")[0]))
            except tk.TclError:
                line = None
        if line is None:
            line = self._selected_line
        if line is None:
            return
        if line not in self._listbox_line_to_headline:
            # If the click landed on a group label, try the next headline line.
            for offset in (1, -1, 2, -2):
                probe = line + offset
                if probe in self._listbox_line_to_headline:
                    line = probe
                    break
        self._select_listbox_line(line)
        detail = self._listbox_line_details.get(line)
        if detail is not None:
            headline_obj = detail.headline
        else:
            headline_index = self._listbox_line_to_headline.get(line)
            if headline_index is None or headline_index < 0 or headline_index >= len(self.headlines):
                return
            headline_obj = self.headlines[headline_index]
        if not isinstance(headline_obj, Headline):
            return
        SummaryWindow(
            self,
            self._headline_with_timezone(headline_obj),
            summary_resolver=resolve_article_summary,
        )


__all__ = ["configure_app_services", "AINewsApp"]
