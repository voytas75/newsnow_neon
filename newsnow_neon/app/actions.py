"""Mute actions helpers for deriving exclusion terms from headlines.

Updates: v0.52 - 2025-11-18 - Extracted mute helpers from controller.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from ...models import Headline

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
    """Derive a source term from the final article domain.

    Resolves redirects (HEAD, GET + meta refresh) to prefer the destination
    site's domain via a lazy import of resolve_final_url. If the final domain
    is a NewsNow redirector (e.g., newsnow.co.uk, newsnow.com, c.newsnow.com),
    fall back to the headline's source label. As a last resort, use the
    original URL's domain if it is not a NewsNow domain.
    """

    url_val = headline.url if isinstance(headline.url, str) else ""
    src_val = headline.source if isinstance(headline.source, str) else ""
    label = src_val.strip() or None

    def _clean_netloc(netloc: str) -> str:
        netloc = netloc.split("@")[-1]
        netloc = netloc.split(":")[0]
        netloc = netloc.lower().strip()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc

    def _is_newsnow(netloc: str) -> bool:
        return (
            netloc.endswith("newsnow.co.uk")
            or netloc.endswith("newsnow.com")
            or netloc == "c.newsnow.com"
        )

    if url_val.strip():
        try:
            original = _clean_netloc(urlparse(url_val).netloc or "")
        except Exception:
            original = ""

        resolved_netloc = original
        try:
            # Lazy import to avoid heavy import graph and cycles.
            from ..http_client import resolve_final_url

            final_url = resolve_final_url(url_val, timeout=8)
            resolved_netloc = _clean_netloc(urlparse(final_url).netloc or "")
        except Exception:
            # If resolution fails, keep original netloc.
            pass

        if resolved_netloc and not _is_newsnow(resolved_netloc):
            return resolved_netloc

        # If destination is still NewsNow or empty, prefer source label.
        if label:
            return label

        # As last resort, avoid returning NewsNow domain.
        if original and not _is_newsnow(original):
            return original

        return None

    return label