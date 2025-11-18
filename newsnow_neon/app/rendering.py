"""Rendering helpers for grouping, relative age labels, and metadata text.

Updates: v0.52 - 2025-11-18 - Extracted UI-agnostic rendering helpers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

from ...models import Headline
from ...utils import parse_iso8601_utc


def group_headlines_by_age(
    entries: Sequence[tuple[int, Headline]]
) -> List[tuple[str, List[tuple[int, Headline, Optional[float]]]]]:
    """Group entries into age buckets for UI display.

    Mirrors controller behavior in
    [application._group_headlines_by_age()](newsnow_neon/application.py:1284).
    """
    buckets: dict[str, list[tuple[int, Headline, Optional[float]]]] = {
        "Last 5 minutes": [],
        "Last 10 minutes": [],
        "Last 30 minutes": [],
        "Older than 1 h": [],
    }
    now_utc = datetime.now(timezone.utc)
    for original_idx, headline in entries:
        age_minutes = headline_age_minutes(headline, now_utc)
        bucket = resolve_age_bucket(age_minutes)
        buckets[bucket].append((original_idx, headline, age_minutes))

    ordered = [
        "Last 5 minutes",
        "Last 10 minutes",
        "Last 30 minutes",
        "Older than 1 h",
    ]
    return [
        (label, buckets.get(label, [])) for label in ordered if buckets.get(label, [])
    ]


def headline_age_minutes(headline: Headline, now_utc: datetime) -> Optional[float]:
    """Compute age in minutes from headline published_at.

    Mirrors
    [application._headline_age_minutes()](newsnow_neon/application.py:1311).
    """
    published_utc = parse_iso8601_utc(headline.published_at)
    if published_utc is None:
        return None
    delta = now_utc - published_utc
    minutes = delta.total_seconds() / 60.0
    return 0.0 if minutes < 0 else minutes


def resolve_age_bucket(age_minutes: Optional[float]) -> str:
    """Resolve age bucket label safely for None or >60 minutes.

    Mirrors
    [application._resolve_age_bucket()](newsnow_neon/application.py:1322).
    """
    if age_minutes is None:
        return "Older than 1 h"
    if age_minutes <= 5:
        return "Last 5 minutes"
    if age_minutes <= 10:
        return "Last 10 minutes"
    if age_minutes <= 30:
        return "Last 30 minutes"
    return "Older than 1 h"


def format_relative_age(age_minutes: Optional[float]) -> Optional[str]:
    """Produce a concise relative age label for UI metadata.

    Mirrors
    [application._format_relative_age()](newsnow_neon/application.py:1335).
    """
    if age_minutes is None:
        return None
    total = int(age_minutes)
    if total < 1:
        return "Just now"
    if total < 60:
        return f"{total}m ago"
    hours, minutes = divmod(total, 60)
    if hours < 24:
        return f"{hours}h {minutes}m ago" if minutes else f"{hours}h ago"
    days, remaining = divmod(hours, 24)
    return f"{days}d {remaining}h ago" if remaining else f"{days}d ago"


def compose_metadata_parts(localized: Headline, relative_label: Optional[str]) -> List[str]:
    """Compose source/time/relative labels; fallback to section or 'Unknown source'.

    Mirrors
    [application._compose_metadata_parts()](newsnow_neon/application.py:1353).
    """
    parts: List[str] = []
    if isinstance(localized.source, str) and localized.source.strip():
        parts.append(localized.source.strip())
    if isinstance(localized.published_time, str) and localized.published_time.strip():
        parts.append(localized.published_time.strip())
    if relative_label:
        parts.append(relative_label)
    if parts:
        return parts
    if isinstance(localized.section, str) and localized.section.strip():
        return [localized.section.strip()]
    return ["Unknown source"]