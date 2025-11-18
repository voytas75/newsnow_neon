"""Headline filtering and exclusion term normalization utilities.

Updates: v0.52 - 2025-11-18 - Extracted pure filtering helpers from controller.
"""

from __future__ import annotations

import re
from typing import Any, List, Sequence, Set

from ...models import Headline


def filter_headlines(
    headlines: Sequence[Headline], exclusion_terms: Set[str]
) -> List[Headline]:
    """Return headlines that do not match any exclusion term.

    Mirrors controller behavior in
    [application._filter_headlines()](newsnow_neon/application.py:1791).
    """
    if not headlines:
        return []
    if not exclusion_terms:
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
        if any(term in haystack for term in exclusion_terms):
            continue
        filtered.append(item)
    return filtered


def normalise_exclusion_terms(source: Any) -> tuple[List[str], Set[str]]:
    """Normalize free-form exclusions into ordered list and set for matching.

    Equivalent to
    [application._normalise_exclusion_terms()](newsnow_neon/application.py:1816).
    """
    candidates: List[str] = []
    if isinstance(source, str):
        candidates.extend(split_exclusion_string(source))
    elif isinstance(source, Sequence) and not isinstance(source, (str, bytes)):
        for item in source:
            if isinstance(item, str):
                candidates.extend(split_exclusion_string(item))

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


def split_exclusion_string(text: str) -> List[str]:
    """Split exclusions by commas, semicolons or whitespace to normalized tokens.

    Matches
    [application._split_exclusion_string()](newsnow_neon/application.py:1839).
    """
    if not isinstance(text, str):
        return []
    raw = re.split(r"[;,]|\s+", text.strip())
    terms = [t.strip().lower() for t in raw if t and t.strip()]
    return terms