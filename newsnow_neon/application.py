"""Tkinter application controller for NewsNow Neon.

Updates: v0.50 - 2025-01-07 - Moved AINewsApp controller and helpers from the legacy script and introduced service injection.
Updates: v0.51 - 2025-10-29 - Wired application metadata import after relocating legacy launcher.
Updates: v0.52 - 2025-11-18 - Added one-click mute source/keyword actions and UI wiring.
Updates: v0.53 - 2025-11-18 - Slimmed controller by delegating background watch and history UI to controllers/helpers, removed duplicate methods.
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from collections import deque
from datetime import datetime, timedelta, timezone, tzinfo
from dataclasses import replace
from tkinter import messagebox
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
import threading
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
    has_highlight_pattern,
    headline_highlight_color,
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
from .settings_store import load_settings, save_settings
from .summaries import configure_litellm_debug
from .ui.windows.summary_window import SummaryWindow
from .ui.windows.keyword_heatmap_window import KeywordHeatmapWindow
from .ui.windows.redis_stats_window import RedisStatsWindow
from .ui.windows.app_info_window import AppInfoWindow
from .utils import parse_iso8601_utc as _parse_iso8601_utc
from .main import APP_METADATA

logger = logging.getLogger(__name__)



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

# Controllers
from .app.controller.refresh_controller import RefreshController
from .app.controller.auto_refresh_controller import AutoRefreshController
from .app.controller.background_watch_controller import (
    BackgroundWatchController,
)
from .app.controller.history_controller import HistoryController
from .app.controller.selection_controller import SelectionController
from .app.controller.exclusions_controller import ExclusionsController
from .app.controller.settings_controller import SettingsController
from .app.controller.redis_controller import RedisController
from .app.controller.highlight_controller import HighlightController
from .app.views.action_bar import build_action_bar
from .app.views.search_filters import build_search_filters
from .app.views.history_panel import build_history_panel
from .app.views.ticker_panel import build_ticker_panel
from .app.views.list_view import build_list_view
from .app.views.logs_panel import build_logs_panel
from .app.views.options_panel import build_options_panel
from .app.views.highlight_panel import build_highlight_panel
from .app.views.controls_panel import build_controls_panel
from .app.renderers.list_renderer import ListRenderer

# Modularized helpers
from .app.filtering import (
    filter_headlines as _filter_headlines_fn,
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
# Controllers and renderer imports (removed duplicate to reduce noise)
# (line preserved intentionally)
#
#
#
#
#
#
#
#
#

from .app.helpers.app_helpers import (
    derive_hover_color,
    profile_name_options,
    sanitize_env_value,
    build_system_rows,
    format_history_entry,
    format_history_tooltip,
)
from .app.ui.ui_helpers import (
    toggle_logs as ui_toggle_logs,
    append_log_line as ui_append_log_line,
    flush_log_buffer as ui_flush_log_buffer,
    handle_log_record as ui_handle_log_record,
    set_options_visibility as ui_set_options_visibility,
    ensure_options_visible as ui_ensure_options_visible,
    update_status_summary as ui_update_status_summary,
    clear_search as ui_clear_search,
    on_search_change as ui_on_search_change,
    on_section_filter_change as ui_on_section_filter_change,
    matches_filters as ui_matches_filters,
    filtered_entries as ui_filtered_entries,
    refresh_section_filter_menu as ui_refresh_section_filter_menu,
    refresh_timezone_menu as ui_refresh_timezone_menu,
    on_timezone_change as ui_on_timezone_change,
    apply_timezone_selection as ui_apply_timezone_selection,
    refresh_timezone_display as ui_refresh_timezone_display,
    apply_color_profile as ui_apply_color_profile,
    choose_color as ui_choose_color,
    update_ticker_colors as ui_update_ticker_colors,
    refresh_profile_menu as ui_refresh_profile_menu,
    on_profile_selected as ui_on_profile_selected,
    refresh_color_profiles as ui_refresh_color_profiles,
    refresh_relative_age_labels as ui_refresh_relative_age_labels,
    clear_headline_list as ui_clear_headline_list,
    clear_listbox_selection as ui_clear_listbox_selection,
    select_listbox_line as ui_select_listbox_line,
)
from .app.ui.history_ui import (
    handle_history_loaded as history_handle_history_loaded,
    on_history_select as history_on_history_select,
    activate_history_selection as history_activate_history_selection,
    on_history_motion as history_on_history_motion,
    capture_live_flow_state as history_capture_live_flow_state,
    apply_history_snapshot as history_apply_history_snapshot,
    restore_live_flow_state as history_restore_live_flow_state,
    exit_history_mode as history_exit_history_mode,
    refresh_history_controls_state as history_refresh_history_controls_state,
)


def _coerce_timezone(name: Optional[str]) -> tuple[str, tzinfo]:
    """Delegate to modular timeutils.coerce_timezone."""
    normalized, zone = _coerce_timezone_fn(name)
    return normalized, zone


def _format_localized_timestamp(timestamp: datetime, zone: tzinfo) -> tuple[str, str]:
    """Delegate to modular timeutils.format_localized_timestamp."""
    return _format_localized_timestamp_fn(timestamp, zone)







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
        # Controllers
        self.refresh_controller = RefreshController(self)
        self.auto_refresh_controller = AutoRefreshController(self)
        self.background_watch_controller = BackgroundWatchController(self)
        self.history_controller = HistoryController(self)
        self.selection_controller = SelectionController(self)
        self.exclusions_controller = ExclusionsController(self)
        self.settings_controller = SettingsController(self)
        self.redis_controller = RedisController(self)
        self.highlight_controller = HighlightController(self)
        self.list_renderer = ListRenderer(self)

        self.log_handler = TkQueueHandler(
            lambda level, message: ui_handle_log_record(self, level, message)
        )
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

        exclusions_list, exclusions_set = self.exclusions_controller.normalise_exclusion_terms(
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
        self._background_refresh_threshold = self.background_watch_controller.coerce_threshold(
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
            "hover": derive_hover_color(
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

        self.ticker, self.full_ticker = build_ticker_panel(self)

        search_frame = build_search_filters(self)
        search_frame.pack(fill="x", padx=10, pady=(0, 5))

        list_frame, self.listbox = build_list_view(self)
        self.listbox.bind("<Button-1>", self.selection_controller.on_click)
        self.listbox.bind("<Double-Button-1>", self.selection_controller.open_selected)
        self.listbox.bind("<Return>", self.selection_controller.open_selected)
        self.listbox.bind("<Up>", lambda event: self.selection_controller.on_nav(-1))
        self.listbox.bind("<Down>", lambda event: self.selection_controller.on_nav(1))
        self.listbox.bind("<Motion>", self.selection_controller.on_motion)
        self.listbox.bind("<Leave>", self.selection_controller.on_leave)
        self.listbox.bind("<Key>", lambda _event: "break")

        build_action_bar(self)

        self.options_container = tk.Frame(self, bg="black")
        self.options_container.pack(fill="x", padx=10, pady=(0, 10))

        build_controls_panel(self)

        build_highlight_panel(self)

        history_controls = build_history_panel(self)

        build_options_panel(self)

        self.log_frame, self.log_text = build_logs_panel(self)
        ui_append_log_line(self, "Logs:")

        self._apply_settings_from_store()
        self._loading_settings = False
        self._save_settings()
        self._log_startup_report()
        self.after(0, self.refresh_headlines)
        self.after(0, lambda: ui_flush_log_buffer(self))
        self.after(0, self.redis_controller.update_redis_meter)
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
        self.redis_controller.update_redis_meter()

    def _open_redis_stats(self) -> None:
        self.redis_controller.open_stats()

    def _load_redis_stats_worker(self) -> None:
        self.redis_controller.load_stats_worker()

    def _handle_redis_stats_ready(self, stats: RedisStatistics) -> None:
        self.redis_controller.handle_stats_ready(stats)

    def _on_redis_stats_closed(self) -> None:
        self.redis_controller.on_stats_closed()

    def _update_redis_meter(self) -> None:
        """Delegate Redis meter updates to RedisController."""
        self.redis_controller.update_redis_meter()

    def refresh_headlines(self, force_refresh: bool = False) -> None:
        """Delegate refresh to RefreshController."""
        self.refresh_controller.refresh(force_refresh=force_refresh)

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
        self.background_watch_controller.update_label()
        self._last_refresh_time = fetched_at
        self._update_content(
            headlines=headlines, ticker_text=ticker_text, from_cache=from_cache
        )
        self.redis_controller.update_redis_meter()
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
        """Delegate to modular rendering.compose_metadata_parts."""
        return _compose_metadata_parts_fn(localized, relative_label)

    def _clear_headline_list(self) -> None:
        """Delegate list clearing to UI helper to keep controller thin."""
        ui_clear_headline_list(self)

    def _clear_listbox_selection(self) -> None:
        """Delegate selection clearing to UI helper."""
        ui_clear_listbox_selection(self)

    def _select_listbox_line(self, line: int) -> None:
        """Delegate line selection to UI helper."""
        ui_select_listbox_line(self, line)

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
                self.list_renderer.append_group_label(f"-- {label} --")
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
                    self.list_renderer.append_headline_row(
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
            self.list_renderer.append_message_line(message)
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
        self.background_watch_controller.recompute_pending()
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
        self._relative_age_job = self.after(60_000, lambda: ui_refresh_relative_age_labels(self))

    def _refresh_relative_age_labels(self) -> None:
        """Delegate to UI helper to reduce controller size."""
        self._relative_age_job = None
        ui_refresh_relative_age_labels(self)

    def _reapply_exclusion_filters(self, *, log_status: bool) -> None:
        self._apply_exclusion_filter_to_state(reschedule=False, log_status=log_status)

    def _apply_exclusion_terms(self, event: Optional[tk.Event] = None) -> Optional[str]:
        return self.exclusions_controller.apply_exclusion_terms(event)

    def _clear_exclusion_terms(self) -> None:
        self.exclusions_controller.clear_exclusion_terms()

    def _filter_headlines(self, headlines: Sequence[Headline]) -> List[Headline]:
        """Delegate to modular filtering.filter_headlines."""
        return _filter_headlines_fn(headlines, self._exclusion_terms)

    def _normalise_exclusion_terms(self, source: Any) -> tuple[List[str], Set[str]]:
        return self.exclusions_controller.normalise_exclusion_terms(source)

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
            enable_keyword = bool(_extract_keyword_for_mute_fn(title_val))
        try:
            self.mute_source_btn.config(
                state=(tk.NORMAL if enable_source else tk.DISABLED)
            )
            self.mute_keyword_btn.config(
                state=(tk.NORMAL if enable_keyword else tk.DISABLED)
            )
        except Exception:
            logger.debug("Unable to update mute action button state.")

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




    def _request_history_refresh(self) -> None:
        """Delegate history refresh workflow to HistoryController."""
        self.history_controller.request_refresh()

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
        history_handle_history_loaded(self, snapshots, error)


    def _on_history_select(self, _event: tk.Event) -> None:
        history_on_history_select(self, _event)

    def _activate_history_selection(
        self, _event: Optional[tk.Event] = None
    ) -> Optional[str]:
        return history_activate_history_selection(self, _event)

    def _on_history_motion(self, event: tk.Event) -> None:
        history_on_history_motion(self, event)

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
        history_apply_history_snapshot(self, snapshot)

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

        system_rows = build_system_rows(SETTINGS_PATH)
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


    def _filtered_entries(self) -> List[tuple[int, Headline]]:
        """Delegate to UI helper for filter matching."""
        return ui_filtered_entries(self)

    def _matches_filters(self, headline: Headline) -> bool:
        """Delegate to UI helper for filter matching."""
        return ui_matches_filters(self, headline)

    def _filters_active(self) -> bool:
        if (self.search_var.get() or "").strip():
            return True
        section_filter = (self.section_filter_var.get() or "").strip()
        return bool(section_filter and section_filter != "All sections")

    def _refresh_section_filter_menu(self, headlines: Sequence[Headline]) -> None:
        ui_refresh_section_filter_menu(self, headlines)

    def _clear_search(self, event: Optional[tk.Event] = None) -> Optional[str]:
        """Delegate to UI helper to clear search."""
        return ui_clear_search(self, event)

    def _on_search_change(self, *_args: object) -> None:
        """Delegate to UI helper for search change handling."""
        ui_on_search_change(self, *_args)

    def _on_section_filter_change(self, *_args: object) -> None:
        """Delegate to UI helper for section filter change handling."""
        ui_on_section_filter_change(self, *_args)

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
        self.redis_controller.update_redis_meter()
        self._pending_new_headlines = 0
        self._last_reported_pending = 0
        self._background_candidate_keys.clear()
        self.background_watch_controller.update_label()
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
        ui_toggle_logs(self)

    def _toggle_options_panel(self) -> None:
        self._set_options_visibility(not self._options_visible)

    def _set_options_visibility(self, visible: bool, *, persist: bool = True) -> None:
        ui_set_options_visibility(self, visible, persist=persist)

    def _ensure_options_visible(self) -> None:
        ui_ensure_options_visible(self)

    def _update_status_summary(self) -> None:
        ui_update_status_summary(self)

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
        self.highlight_controller.update_keywords_setting(
            raw_value,
            refresh_views=refresh_views,
            persist=persist,
            show_feedback=show_feedback,
        )

    def apply_highlight_keywords_from_var(self, *, show_feedback: bool) -> None:
        self.highlight_controller.apply_keywords_from_var(
            show_feedback=show_feedback
        )

    def _on_highlight_keywords_return(self, *_args: object) -> str:
        self.highlight_controller.on_return()
        return "break"

    def _on_highlight_keywords_button(self) -> None:
        self.highlight_controller.on_apply_button()


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
            if (sanitized := sanitize_env_value(name, value)) is not None
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
        self.background_watch_controller.update_label()
        self._save_settings()
        self._schedule_background_watch(immediate=enabled)
        if enabled:
            self.background_watch_controller.maybe_auto_refresh_for_pending()
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
        self.auto_refresh_controller.cancel_pending_jobs()

    def _schedule_auto_refresh(self) -> None:
        self.auto_refresh_controller.schedule()

    def _schedule_auto_refresh_with_delay(self, delay_ms: int) -> None:
        self.auto_refresh_controller.schedule_with_delay(delay_ms)

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
        """Delegate to BackgroundWatchController."""
        self.background_watch_controller.schedule(immediate=immediate)

    def _schedule_background_watch_with_delay(self, delay_ms: int) -> None:
        """Delegate to BackgroundWatchController."""
        self.background_watch_controller.schedule_with_delay(delay_ms)

    def _cancel_background_watch(self) -> None:
        """Delegate to BackgroundWatchController."""
        self.background_watch_controller.cancel()

    def _background_watch_trigger(self) -> None:
        """Delegate to BackgroundWatchController."""
        self.background_watch_controller.trigger()

    def _background_watch_worker(self) -> None:
        self.background_watch_controller.worker()

    def _handle_background_watch_failure(self) -> None:
        self.background_watch_controller.handle_failure()

    def _handle_background_watch_result(self, headlines: List[Headline]) -> None:
        self.background_watch_controller.handle_result(headlines)

    def _update_background_watch_label(self) -> None:
        self.background_watch_controller.update_label()

    @staticmethod
    def _headline_key(headline: Headline) -> tuple[str, str]:
        title = headline.title.strip().lower() if isinstance(headline.title, str) else ""
        url = headline.url.strip() if isinstance(headline.url, str) else ""
        return title, url


    def _apply_background_watch_threshold(self, *_args: object) -> None:
        self.background_watch_controller.apply_threshold()


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
        ui_handle_log_record(self, level, message)

    def _flush_log_buffer(self) -> None:
        ui_flush_log_buffer(self)

    def _append_log_line(self, message: str) -> None:
        ui_append_log_line(self, message)

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
                "hover": derive_hover_color(text_color),
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
        threshold = self.background_watch_controller.coerce_threshold(
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
        self.background_watch_controller.update_label()
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
            "hover": derive_hover_color(self.settings["custom_text"]),
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
        self._background_refresh_threshold = self.background_watch_controller.coerce_threshold(
            self.settings["background_watch_refresh_threshold"]
        )
        self.background_watch_threshold_var.set(self._background_refresh_threshold)
        self._pending_new_headlines = 0
        self._last_reported_pending = 0
        self._background_candidate_keys.clear()
        self.background_watch_controller.update_label()
        self._save_settings()
        self._schedule_auto_refresh()
        self._schedule_background_watch(immediate=bool(self.background_watch_var.get()))
        self._log_status("Settings reset to defaults.")

    def _apply_color_profile(self, selected: Optional[str] = None) -> None:
        ui_apply_color_profile(self, selected)

    def _choose_color(self, target: str) -> None:
        ui_choose_color(self, target)

    def _update_ticker_colors(self) -> None:
        ui_update_ticker_colors(self)

    def _refresh_profile_menu(self) -> None:
        ui_refresh_profile_menu(self)

    def _refresh_timezone_menu(self) -> None:
        ui_refresh_timezone_menu(self)

    def _on_timezone_change(self, *_args: object) -> None:
        ui_on_timezone_change(self, *_args)

    def _apply_timezone_selection(self, value: str, *, persist: bool) -> None:
        ui_apply_timezone_selection(self, value, persist=persist)

    def _refresh_timezone_display(self) -> None:
        ui_refresh_timezone_display(self)

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
