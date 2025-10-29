"""Keyword highlight configuration, colour helpers, and tooltip utilities."""

from __future__ import annotations

import os
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

from .models import Headline, KeywordHeatmapData

# --- Highlight keyword registry ----------------------------------------------------------------

DEFAULT_HIGHLIGHT_KEYWORDS: Dict[str, str] = {
    ". AI ": "#FFD54F",
    " AI ": "#FFD54F",
    "AI ": "#FFD54F",
    " AI.": "#FFD54F",
    "Cybersecurity": "#FF0000",
    "Tesla": "#4DD0E1",
    "Ransom": "#FF0000",
    "zero-day": "#FF0000",
    "vulnerability": "#FF0000",
    "Quantum": "#8E44AD",
    "Microsoft": "#0078D4",
    "OpenAI": "#10A37F",
    "chatgpt": "#10A37F",
    "cybercrime": "#FF0000",
    "apple": "#A2AAAD",
    "iphone": "#A2AAAD",
    "ipad": "#A2AAAD",
}


def _normalize_hex_color(candidate: str, fallback: str) -> str:
    value = candidate.strip()
    if not value:
        return fallback
    if value.startswith("#") and len(value) in {4, 7}:
        return value
    if re.fullmatch(r"[0-9a-fA-F]{6}", value):
        return f"#{value}"
    return fallback


def parse_highlight_keywords(
    raw: Optional[str],
    fallback: Mapping[str, str],
    *,
    allow_empty_fallback: bool = True,
) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if raw is not None:
        for chunk in raw.split(";"):
            if not chunk.strip():
                continue
            if ":" in chunk:
                key, color = chunk.split(":", 1)
            else:
                key, color = chunk, ""
            keyword = key.strip()
            if not keyword:
                continue
            normalized_color = _normalize_hex_color(
                color, fallback.get(keyword, "#FFD54F")
            )
            mapping[keyword] = normalized_color
    if mapping:
        return mapping
    return dict(fallback) if allow_empty_fallback else {}


def _load_highlight_keywords() -> Dict[str, str]:
    raw = os.getenv("NEWS_HIGHLIGHT_KEYWORDS")
    return parse_highlight_keywords(raw, DEFAULT_HIGHLIGHT_KEYWORDS)


_ENV_HIGHLIGHT_KEYWORDS: Dict[str, str] = _load_highlight_keywords()
ENV_HIGHLIGHT_KEYWORDS: Dict[str, str] = dict(_ENV_HIGHLIGHT_KEYWORDS)

HIGHLIGHT_KEYWORDS: Dict[str, str] = {}
HIGHLIGHT_LOOKUP: Dict[str, str] = {}
HIGHLIGHT_PATTERN: Optional[re.Pattern[str]] = None
HEATMAP_LABEL_LOOKUP: Dict[str, str] = {}
HEATMAP_COLOR_LOOKUP: Dict[str, str] = {}


def apply_highlight_keywords(mapping: Mapping[str, str]) -> None:
    """Apply keywords for highlighting and rebuild lookup caches."""

    global HIGHLIGHT_KEYWORDS, HIGHLIGHT_LOOKUP, HIGHLIGHT_PATTERN
    global HEATMAP_LABEL_LOOKUP, HEATMAP_COLOR_LOOKUP
    HIGHLIGHT_KEYWORDS = dict(mapping)
    HIGHLIGHT_LOOKUP = {
        key.lower(): value for key, value in HIGHLIGHT_KEYWORDS.items()
    }
    if HIGHLIGHT_LOOKUP:
        escaped_terms = [re.escape(term) for term in HIGHLIGHT_KEYWORDS]
        keyword_pattern = "|".join(escaped_terms)
        HIGHLIGHT_PATTERN = re.compile(keyword_pattern, re.IGNORECASE)
    else:
        HIGHLIGHT_PATTERN = None
    HEATMAP_LABEL_LOOKUP = {
        key.lower(): (key.strip() or key) for key in HIGHLIGHT_KEYWORDS
    }
    HEATMAP_COLOR_LOOKUP = {}
    for raw_keyword, color in HIGHLIGHT_KEYWORDS.items():
        label = raw_keyword.strip() or raw_keyword
        HEATMAP_COLOR_LOOKUP.setdefault(label, color)


apply_highlight_keywords(ENV_HIGHLIGHT_KEYWORDS)


# --- Tooltip and headline helpers --------------------------------------------------------------

def compose_headline_tooltip(
    headline: Headline, *, relative_age: Optional[str] = None
) -> str:
    """Build a multiline tooltip string with headline metadata."""

    title = headline.title.strip() if isinstance(headline.title, str) else ""
    lines: List[str] = [title or "Untitled headline"]
    metadata: List[str] = []

    if isinstance(headline.source, str) and headline.source.strip():
        metadata.append(f"Source: {headline.source.strip()}")
    if isinstance(headline.section, str) and headline.section.strip():
        metadata.append(f"Section: {headline.section.strip()}")
    published_label: Optional[str] = None
    if isinstance(headline.published_time, str) and headline.published_time.strip():
        published_label = headline.published_time.strip()
    elif isinstance(headline.published_at, str) and headline.published_at.strip():
        published_label = headline.published_at.strip()
    if published_label:
        metadata.append(f"Published: {published_label}")
    if relative_age:
        metadata.append(f"Age: {relative_age}")
    domain = urlparse(headline.url).netloc
    if domain.startswith("www."):
        domain = domain[4:]
    if domain:
        metadata.append(f"Source URL: {domain}")
    if isinstance(headline.url, str) and headline.url.strip():
        metadata.append(f"Link: {headline.url.strip()}")

    if metadata:
        lines.extend(metadata)
    return "\n".join(lines)


def highlight_segments(text: str) -> List[Tuple[str, Optional[str]]]:
    if not text:
        return [("", None)]
    if HIGHLIGHT_PATTERN is None:
        return [(text, None)]
    segments: List[Tuple[str, Optional[str]]] = []
    last_index = 0
    for match in HIGHLIGHT_PATTERN.finditer(text):
        start, end = match.span()
        if start > last_index:
            segments.append((text[last_index:start], None))
        matched = text[start:end]
        color = HIGHLIGHT_LOOKUP.get(match.group(0).lower())
        segments.append((matched, color))
        last_index = end
    if last_index < len(text):
        segments.append((text[last_index:], None))
    return segments or [(text, None)]


def first_highlight_color(text: Optional[str]) -> Optional[str]:
    if not text or HIGHLIGHT_PATTERN is None:
        return None
    match = HIGHLIGHT_PATTERN.search(text)
    if not match:
        return None
    return HIGHLIGHT_LOOKUP.get(match.group(0).lower())


def headline_highlight_color(headline: Headline) -> Optional[str]:
    for candidate in (
        headline.title,
        headline.source,
        headline.section,
    ):
        color = first_highlight_color(candidate)
        if color:
            return color
    return None


HEATMAP_FALLBACK_COLOR = "#4DA6FF"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    candidate = value.strip().lstrip("#")
    if len(candidate) == 3:
        candidate = "".join(ch * 2 for ch in candidate)
    if len(candidate) != 6:
        raise ValueError(f"Invalid hex color '{value}'.")
    return tuple(int(candidate[i : i + 2], 16) for i in range(0, 6, 2))


def _rgb_to_hex(values: tuple[int, int, int]) -> str:
    red, green, blue = values
    return f"#{red:02X}{green:02X}{blue:02X}"


def blend_hex(background: str, foreground: str, factor: float) -> str:
    blend_factor = max(0.0, min(1.0, factor))
    bg_rgb = _hex_to_rgb(background)
    fg_rgb = _hex_to_rgb(foreground)
    mixed = tuple(
        int(round(bg + (fg - bg) * blend_factor))
        for bg, fg in zip(bg_rgb, fg_rgb)
    )
    return _rgb_to_hex(mixed)


def build_keyword_heatmap_data(headlines: Sequence[Headline]) -> Optional[KeywordHeatmapData]:
    """Aggregate keyword frequency data for the heatmap view."""

    if not headlines or HIGHLIGHT_PATTERN is None:
        return None

    sections: List[str] = []
    section_totals: Dict[str, int] = {}
    keyword_order: List[str] = []
    keyword_seen: set[str] = set()
    counts: Dict[str, Dict[str, int]] = {}

    for headline in headlines:
        section_raw = headline.section if isinstance(headline.section, str) else ""
        section = section_raw.strip() or "Uncategorised"
        if section not in section_totals:
            section_totals[section] = 0
            sections.append(section)
            counts[section] = {}
        section_totals[section] += 1

        title = headline.title if isinstance(headline.title, str) else ""
        if not title or HIGHLIGHT_PATTERN is None:
            continue
        matches = list(HIGHLIGHT_PATTERN.finditer(title))
        if not matches:
            continue

        section_counts = counts[section]
        for match in matches:
            lookup_key = match.group(0).lower()
            label = HEATMAP_LABEL_LOOKUP.get(lookup_key)
            if label is None:
                label = match.group(0).strip() or match.group(0)
            section_counts[label] = section_counts.get(label, 0) + 1
            if label not in keyword_seen:
                keyword_seen.add(label)
                keyword_order.append(label)

    if not keyword_seen:
        return None

    for section in sections:
        section_counts = counts[section]
        for label in keyword_order:
            section_counts.setdefault(label, 0)

    keyword_colors = {
        label: HEATMAP_COLOR_LOOKUP.get(label, HEATMAP_FALLBACK_COLOR)
        for label in keyword_order
    }

    max_density = 0.0
    for section in sections:
        total = max(section_totals.get(section, 0), 1)
        for label in keyword_order:
            density = section_counts[label] / total
            if density > max_density:
                max_density = density

    return KeywordHeatmapData(
        sections=sections,
        keywords=keyword_order,
        counts=counts,
        totals=section_totals,
        keyword_colors=keyword_colors,
        max_density=max_density,
    )


__all__ = [
    "DEFAULT_HIGHLIGHT_KEYWORDS",
    "HIGHLIGHT_KEYWORDS",
    "ENV_HIGHLIGHT_KEYWORDS",
    "apply_highlight_keywords",
    "blend_hex",
    "build_keyword_heatmap_data",
    "compose_headline_tooltip",
    "headline_highlight_color",
    "highlight_segments",
    "first_highlight_color",
    "HEATMAP_FALLBACK_COLOR",
    "parse_highlight_keywords",
    "has_highlight_pattern",
    "HIGHLIGHT_PATTERN",
    "HIGHLIGHT_LOOKUP",
    "HEATMAP_LABEL_LOOKUP",
    "HEATMAP_COLOR_LOOKUP",
    "relative_luminance",
]
def relative_luminance(hex_color: str) -> float:
    red, green, blue = _hex_to_rgb(hex_color)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def has_highlight_pattern() -> bool:
    return HIGHLIGHT_PATTERN is not None
