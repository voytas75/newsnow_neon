"""Configuration primitives and static data for NewsNow Neon.

This module centralises application constants, default settings, colour
profiles, and cache paths so other layers can import them without triggering
side effects from the legacy monolithic script.

Updates: v0.49.1 - 2025-01-07 - Extracted configuration and defaults into a standalone module.
Updates: v0.50 - 2025-01-07 - Added background watch scheduling defaults for the modular application.
"""

from __future__ import annotations

import os
from datetime import timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv as _config_load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    _config_load_dotenv = None
else:
    _config_load_dotenv()

from .models import NewsSection

# --- Headline sections and scraping options ----------------------------------------------------

SECTIONS: list[NewsSection] = [
    NewsSection("Tech latest", "https://www.newsnow.com/us/Tech?type=ln"),
    NewsSection("Science latest", "https://www.newsnow.com/us/Science?type=ln"),
]

REQUEST_SELECTORS: list[str] = [
    "a.newsfeed__title-link",
    "a.nn-feed-item__title-link",
    "div.newsfeed a",
    "#newsfeed a",
    "article a",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
)

SECTION_CUTOFF_TOKENS: tuple[str, ...] = (
    "more topics",
    "more news",
    "more stories",
)
SECTION_CUTOFF_TAGS: set[str] = {"h1", "h2", "h3", "h4", "h5", "h6", "header"}


# --- Redis and historical caching --------------------------------------------------------------

CACHE_KEY = os.getenv("NEWS_CACHE_KEY", "ainews:headlines:v1")
try:
    CACHE_TTL_SECONDS = max(60, int(os.getenv("NEWS_CACHE_TTL", "900")))
except ValueError:
    CACHE_TTL_SECONDS = 900

HISTORICAL_CACHE_PREFIX = os.getenv("NEWS_HISTORY_PREFIX", "news")
try:
    HISTORICAL_CACHE_TTL_SECONDS = max(
        300, int(os.getenv("NEWS_HISTORY_TTL", "86400"))
    )
except ValueError:
    HISTORICAL_CACHE_TTL_SECONDS = 86400

_historical_cache_enabled = True


def set_historical_cache_enabled(enabled: bool) -> None:
    """Toggle the optional historical cache layer."""

    global _historical_cache_enabled
    _historical_cache_enabled = bool(enabled)


def is_historical_cache_enabled() -> bool:
    return _historical_cache_enabled


REDIS_URL = os.getenv("REDIS_URL")


# --- Timezone defaults -------------------------------------------------------------------------

DEFAULT_TIMEZONE = "Europe/Berlin"
TIMEZONE_CHOICES: list[str] = [
    "Europe/Berlin",
    "UTC",
    "Europe/London",
    "Europe/Paris",
    "US/Eastern",
    "US/Central",
    "US/Pacific",
    "Asia/Tokyo",
    "Asia/Kolkata",
    "Australia/Sydney",
]

_FIXED_ZONE_FALLBACKS: Dict[str, tzinfo] = {
    "UTC": timezone.utc,
    "Europe/Berlin": timezone(timedelta(hours=1), name="CET"),
    "Europe/Paris": timezone(timedelta(hours=1), name="CET"),
    "Europe/London": timezone.utc,
    "US/Eastern": timezone(-timedelta(hours=5), name="EST"),
    "US/Central": timezone(-timedelta(hours=6), name="CST"),
    "US/Pacific": timezone(-timedelta(hours=8), name="PST"),
    "Asia/Tokyo": timezone(timedelta(hours=9), name="JST"),
    "Asia/Kolkata": timezone(timedelta(hours=5, minutes=30), name="IST"),
    "Australia/Sydney": timezone(timedelta(hours=10), name="AEST"),
}


def fixed_zone_fallback(name: str) -> Optional[tzinfo]:
    return _FIXED_ZONE_FALLBACKS.get(name)


# --- Colour profiles and defaults --------------------------------------------------------------

COLOR_PROFILES: Dict[str, Dict[str, str]] = {
    "Classic Ticker": {
        "background": "#000000",
        "text": "#FFD60A",
        "hover": "#FF8C00",
    },
    "Ocean Breeze": {
        "background": "#0B3D91",
        "text": "#E0FBFC",
        "hover": "#98C1D9",
    },
    "Terminal Green": {
        "background": "#001F0F",
        "text": "#39FF14",
        "hover": "#7DFF61",
    },
    "Sunset Glow": {
        "background": "#2C061F",
        "text": "#FF9966",
        "hover": "#FFB347",
    },
    "Aurora Night": {
        "background": "#011826",
        "text": "#13F2ED",
        "hover": "#50F5C4",
    },
    "Monochrome Slate": {
        "background": "#1F1F1F",
        "text": "#E0E0E0",
        "hover": "#9E9E9E",
    },
}
DEFAULT_COLOR_PROFILE_NAME = next(iter(COLOR_PROFILES))
DEFAULT_COLOR_PROFILE = COLOR_PROFILES[DEFAULT_COLOR_PROFILE_NAME]
CUSTOM_PROFILE_NAME = "Custom"


def register_color_profile(
    name: str, background: str, text: str, hover: Optional[str] = None
) -> None:
    """Add or overwrite a colour profile."""

    COLOR_PROFILES[name] = {
        "background": background,
        "text": text,
        "hover": hover or text,
    }


# --- Settings persistence ----------------------------------------------------------------------

_LOCAL_APPDATA = os.getenv("LOCALAPPDATA")
_XDG_CONFIG_HOME = os.getenv("XDG_CONFIG_HOME")

if os.name == "nt":
    base_dir = (
        Path(_LOCAL_APPDATA)
        if _LOCAL_APPDATA
        else Path.home() / "AppData" / "Local"
    )
    _DEFAULT_SETTINGS_FILE = base_dir / "NewsNowNeon" / "ainews_settings.json"
else:
    base_dir = (
        Path(_XDG_CONFIG_HOME)
        if _XDG_CONFIG_HOME
        else Path.home() / ".config"
    )
    _DEFAULT_SETTINGS_FILE = base_dir / "NewsNowNeon" / "ainews_settings.json"

SETTINGS_PATH = Path(os.getenv("NEWS_APP_SETTINGS", str(_DEFAULT_SETTINGS_FILE)))

DEFAULT_SETTINGS: Dict[str, Any] = {
    "ticker_speed": 2,
    "color_profile": DEFAULT_COLOR_PROFILE_NAME,
    "custom_background": DEFAULT_COLOR_PROFILE["background"],
    "custom_text": DEFAULT_COLOR_PROFILE["text"],
    "log_visible": False,
    "debug_mode": False,
    "window_geometry": "900x450",
    "litellm_debug": False,
    "auto_refresh_enabled": True,
    "auto_refresh_minutes": 5,
    "timezone": DEFAULT_TIMEZONE,
    "historical_cache_enabled": True,
    "background_watch_enabled": False,
    "background_watch_refresh_threshold": 30,
    "headline_exclusions": [],
    "options_visible": False,
    "highlight_keywords": "",
}

# --- Background watch defaults ------------------------------------------------

BACKGROUND_WATCH_INTERVAL_SECONDS = 90
BACKGROUND_WATCH_INTERVAL_MS = BACKGROUND_WATCH_INTERVAL_SECONDS * 1000
BACKGROUND_WATCH_INITIAL_DELAY_MS = 15_000


def merge_settings(overrides: Mapping[str, Any]) -> Dict[str, Any]:
    """Apply overrides on top of the default settings."""

    merged = DEFAULT_SETTINGS.copy()
    merged.update({key: value for key, value in overrides.items() if key in merged})
    return merged


set_historical_cache_enabled(DEFAULT_SETTINGS["historical_cache_enabled"])


__all__ = [
    "CACHE_KEY",
    "CACHE_TTL_SECONDS",
    "COLOR_PROFILES",
    "CUSTOM_PROFILE_NAME",
    "DEFAULT_COLOR_PROFILE",
    "DEFAULT_COLOR_PROFILE_NAME",
    "DEFAULT_SETTINGS",
    "DEFAULT_TIMEZONE",
    "HISTORICAL_CACHE_PREFIX",
    "HISTORICAL_CACHE_TTL_SECONDS",
    "REQUEST_SELECTORS",
    "SECTIONS",
    "SECTION_CUTOFF_TAGS",
    "SECTION_CUTOFF_TOKENS",
    "SETTINGS_PATH",
    "TIMEZONE_CHOICES",
    "USER_AGENT",
    "merge_settings",
    "register_color_profile",
    "is_historical_cache_enabled",
    "set_historical_cache_enabled",
    "REDIS_URL",
    "fixed_zone_fallback",
    "BACKGROUND_WATCH_INTERVAL_SECONDS",
    "BACKGROUND_WATCH_INTERVAL_MS",
    "BACKGROUND_WATCH_INITIAL_DELAY_MS",
]
