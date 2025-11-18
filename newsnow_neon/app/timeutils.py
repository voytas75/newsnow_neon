"""Timezone coercion and localized timestamp formatting utilities.

Updates: v0.52 - 2025-11-18 - Extracted time helpers from controller.
"""

from __future__ import annotations

import logging
from datetime import datetime, tzinfo, timezone

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..config import DEFAULT_TIMEZONE, fixed_zone_fallback

logger = logging.getLogger(__name__)


def coerce_timezone(name: str | None) -> tuple[str, tzinfo]:
    """Coerce a timezone name to ZoneInfo or a fixed offset, fallback to UTC.

    Mirrors controller behavior in
    [application._coerce_timezone()](newsnow_neon/application.py:171).
    """
    candidate = (name or "").strip() or DEFAULT_TIMEZONE
    try:
        zone = ZoneInfo(candidate)
        return candidate, zone
    except ZoneInfoNotFoundError:
        fallback = fixed_zone_fallback(candidate)
        if fallback is not None:
            logger.debug(
                "IANA timezone '%s' unavailable; using fixed offset fallback.",
                candidate or "<empty>",
            )
            return candidate, fallback
        logger.warning(
            "Unknown timezone '%s'; falling back to UTC.", candidate or "<empty>"
        )
        return "UTC", timezone.utc


def format_localized_timestamp(timestamp: datetime, zone: tzinfo) -> tuple[str, str]:
    """Format a localized HH:MM label and ISO datetime in the given zone.

    Mirrors controller behavior in
    [application._format_localized_timestamp()](newsnow_neon/application.py:191).
    """
    local_dt = timestamp.astimezone(zone)
    return local_dt.strftime("%H:%M %Z"), local_dt.isoformat()