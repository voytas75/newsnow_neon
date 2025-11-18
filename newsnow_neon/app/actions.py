"""Mute actions helpers for deriving exclusion terms from headlines.

Updates: v0.52 - 2025-11-18 - Extracted mute helpers from controller.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from ..models import Headline

_MUTE_STOPWORDS: set[str] = {
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


def extract_keyword_for_mute(title: str) -> Optional[str]:
    """Extract a simple, useful keyword from a headline title.

    Mirrors controller behavior in
    [application._extract_keyword_for_mute()](newsnow_neon/application.py:1889).
    """
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


def derive_source_term(headline: Headline) -> Optional[str]:
    """Derive a source term from URL netloc, falling back to source label.

    Mirrors controller logic in
    [application._mute_selected_source()](newsnow_neon/application.py:1954).
    """
    url_val = headline.url if isinstance(headline.url, str) else ""
    if url_val.strip():
        try:
            parsed = urlparse(url_val)
            netloc = parsed.netloc or ""
            netloc = netloc.split("@")[-1]
            netloc = netloc.split(":")[0]
            netloc = netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            if netloc:
                return netloc
        except Exception:
            # Fall back to source label below
            pass
    src_val = headline.source if isinstance(headline.source, str) else ""
    label = src_val.strip()
    return label or None