"""UI helper functions extracted from the application controller.

Updates: v0.52 - 2025-11-18 - Extracted color, env, system, and history helpers
into a dedicated module to slim down the main application controller.
"""

from __future__ import annotations

import platform
import re
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime, tzinfo

from ..config import COLOR_PROFILES, CUSTOM_PROFILE_NAME
from ..models import HistoricalSnapshot


_SENSITIVE_ENV_PATTERN = re.compile(
    r"(KEY|TOKEN|SECRET|PASSWORD|API_KEY)$", re.IGNORECASE
)


def derive_hover_color(hex_color: str, factor: float = 0.25) -> str:
    """Derive a lighter hover color from a hex color value.

    Returns the input value unchanged if it is not a valid hex color.
    """
    if not isinstance(hex_color, str) or not hex_color.startswith("#"):
        return hex_color

    hex_value = hex_color.lstrip("#")
    if len(hex_value) == 3:
        hex_value = "".join(ch * 2 for ch in hex_value)
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


def profile_name_options() -> List[str]:
    """Return available color profile names, ensuring CUSTOM is last."""
    names = list(COLOR_PROFILES.keys())
    if CUSTOM_PROFILE_NAME not in COLOR_PROFILES:
        names.append(CUSTOM_PROFILE_NAME)
    else:
        names = [n for n in names if n != CUSTOM_PROFILE_NAME] + [CUSTOM_PROFILE_NAME]
    return names


def sanitize_env_value(name: str, value: Optional[str]) -> Optional[str]:
    """Mask sensitive environment variable values for safe logging.

    Returns:
        - "***" for sensitive keys with a value
        - None for empty values
        - Truncated long values (> 80 chars)
        - Original value otherwise
    """
    if value is None:
        return None
    if _SENSITIVE_ENV_PATTERN.search(name) or any(
        token in name for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")
    ):
        return "***" if value else None
    if len(value) > 80:
        return value[:77] + "…"
    return value


def build_system_rows(settings_path: Path | str) -> List[Tuple[str, str]]:
    """Compose key-value rows describing the host system and settings path."""
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

    rows: List[Tuple[str, str]] = [("Operating system", os_summary)]
    if machine:
        rows.append(("Machine", machine))
    if processor and processor.lower() != "unknown":
        rows.append(("Processor", processor))
    rows.append(("Python", f"{python_impl} {python_version}".strip()))
    rows.append(("Settings file", str(settings_path)))
    return rows


def format_history_entry(
    snapshot: HistoricalSnapshot, tz: tzinfo, tz_name: str
) -> str:
    """Format a snapshot entry label for the history listbox."""
    local_dt = snapshot.captured_at.astimezone(tz)
    tz_label = local_dt.tzname() or tz_name
    timestamp = local_dt.strftime("%Y-%m-%d %H:%M")
    headline_label = "headline" if snapshot.headline_count == 1 else "headlines"
    return f"{timestamp} {tz_label} • {snapshot.headline_count} {headline_label}"


def format_history_tooltip(
    snapshot: HistoricalSnapshot, tz: tzinfo, tz_name: str
) -> str:
    """Compose a multi-line tooltip for a snapshot listbox hover."""
    local_dt = snapshot.captured_at.astimezone(tz)
    tz_label = local_dt.tzname() or tz_name
    lines = [
        f"Captured: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_label}",
        f"Redis key: {snapshot.key}",
        f"Headlines: {snapshot.headline_count}",
    ]
    if snapshot.summary_count:
        lines.append(f"Summaries: {snapshot.summary_count}")
    ticker_preview = snapshot.cache.ticker_text or ""
    if ticker_preview:
        truncated = (
            ticker_preview
            if len(ticker_preview) <= 120
            else ticker_preview[:117].rstrip() + "…"
        )
        lines.append(f"Ticker: {truncated}")
    return "\n".join(lines)