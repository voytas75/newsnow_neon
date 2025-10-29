"""Tkinter dashboard for NewsNow headlines with caching and LLM summaries.

This module powers the NewsNow Neon desktop app. It scrapes headlines from
NewsNow, shows them in a scrolling ticker, and offers optional article
summaries through LiteLLM providers. Settings are persisted under
``%LOCALAPPDATA%\\NewsNowNeon`` (configurable with ``NEWS_APP_SETTINGS``), and a
Redis cache keeps recently fetched headlines warm when ``REDIS_URL`` is set.

Summaries can target a dedicated model by exporting ``NEWS_SUMMARY_*``
environment variables (model, provider, API base, keys, Azure deployment
details). If those overrides are absent, the app reuses the default LiteLLM
configuration defined by ``LITELLM_*`` variables.

Updates: v0.3 - 2025-10-27 - Persist ticker and article summaries in the Redis cache for offline availability.
Updates: v0.4 - 2025-10-27 - Remember main window geometry in user settings when available.
Updates: v0.5 - 2025-10-27 - Hardened article summarisation with multi-attempt fetch and cache reuse.
Updates: v0.6 - 2025-10-27 - Added LiteLLM debug toggle alongside existing debug logs control.
Updates: v0.7 - 2025-10-27 - Introduced configurable auto-refresh with five-minute default.
Updates: v0.8 - 2025-10-27 - Capture NewsNow source and publish time metadata for each headline.
Updates: v0.9 - 2025-10-27 - Align list view metadata with scraped source and publish time.
Updates: v0.10 - 2025-10-27 - Avoid showing NewsNow redirect domain when source metadata is missing.
Updates: v0.11 - 2025-10-27 - Parse alternate NewsNow article card markup for source metadata.
Updates: v0.12 - 2025-10-27 - Use scraped publish times in the secondary ticker.
Updates: v0.13 - 2025-10-27 - Added configurable timezone for publish timestamps with CET default.
Updates: v0.14 - 2025-10-27 - Grouped list view by headline age and aligned auto refresh with manual refresh.
Updates: v0.15 - 2025-10-27 - Reused pooled HTTP sessions, limited article fetch budget, and streamlined Redis writes.
Updates: v0.16 - 2025-10-27 - Added headline search and section filtering in the desktop UI.
Updates: v0.17 - 2025-10-27 - Highlight configurable keywords (AI, Cybersecurity, Tesla) across tickers and summaries.
Updates: v0.18 - 2025-10-27 - Surface full headline details via hover tooltips in ticker and list views.
Updates: v0.19 - 2025-10-27 - Provide keyword frequency heatmap visualization across feeds.
Updates: v0.20 - 2025-10-27 - Maintain optional 24h Redis history snapshots with a default-on toggle.
Updates: v0.21 - 2025-10-27 - Added Info dialog with system snapshot and support links.
Updates: v0.22 - 2025-10-27 - Introduced Exit button for graceful shutdown.
Updates: v0.23 - 2025-10-27 - Allow defining exclusion terms to filter headlines from tickers and lists.
Updates: v0.24 - 2025-10-27 - Added Redis statistics dialog and diagnostics button for cache insights.
Updates: v0.25 - 2025-10-27 - Grouped refresh timers with auto controls and track elapsed time since the last update.
Updates: v0.26 - 2025-10-27 - Added history mode UI backed by 24h Redis snapshots for read-only browsing.
Updates: v0.27 - 2025-10-27 - Refresh list view relative age labels every minute to keep timestamps current.
Updates: v0.28 - 2025-10-28 - Added background watch toggle to count unseen headlines in real time.
Updates: v0.29 - 2025-10-28 - Sync headline hover metadata with the selected timezone.
Updates: v0.30 - 2025-10-28 - Keep neon tickers live while browsing history snapshots and name key widgets.
Updates: v0.31 - 2025-10-28 - Restore live tickers when returning from history snapshots.
Updates: v0.32 - 2025-10-28 - Auto-refresh when unseen headline threshold is reached via background watch.
Updates: v0.33 - 2025-10-28 - Moved exclusion filter controls alongside search and section filters.
Updates: v0.34 - 2025-10-28 - Preserve live refresh flow when exiting Redis history snapshots.
Updates: v0.35 - 2025-10-28 - Trigger immediate auto-refresh when unseen headline threshold is exceeded.
Updates: v0.36 - 2025-10-28 - Collapsed advanced controls behind a toggleable Options panel.
Updates: v0.37 - 2025-10-28 - Added top-level refresh and compact status summary when options are hidden.
Updates: v0.38 - 2025-10-28 - Aligned Info and Exit buttons on the action bar to the right edge.
Updates: v0.39 - 2025-10-28 - Made highlight keywords configurable via the settings panel.
Updates: v0.40 - 2025-10-28 - Added confirmation dialog before resetting settings to defaults.
Updates: v0.41 - 2025-10-28 - Prevented highlight updates from resetting ticker animation flow.
Updates: v0.42 - 2025-10-28 - Ensure summary window layout keeps action buttons visible by default.
Updates: v0.43 - 2025-10-28 - Preserve highlight priority so earlier keywords win overlapping matches.
Updates: v0.44 - 2025-10-28 - Render summary metadata inline with italic styling for improved readability.
Updates: v0.45 - 2025-10-28 - Render list view metadata in smaller italic styling beneath each headline title.
Updates: v0.46 - 2025-10-28 - Display metadata inline with headlines in the main list using italic styling.
Updates: v0.47 - 2025-10-28 - Match cached summaries to headline titles to prevent mismatched preview content.
Updates: v0.48 - 2025-10-28 - Keep list selection stable when opening summaries and ensure the first item highlights.
Updates: v0.49 - 2025-10-28 - Tag list rows to make first-headline selections reliable next to group headers.
Updates: v0.50 - 2025-01-07 - Delegated UI/controller logic to package modules and split settings, HTTP, and summary utilities.
Updates: v0.51 - 2025-10-29 - Migrated legacy launcher into the package namespace and stabilised sys.path bootstrapping.
"""

from __future__ import annotations

import logging
import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

if __package__ in {None, ""}:
    import pathlib
    import sys

    _PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent
    _PARENT = _PACKAGE_ROOT.parent
    if str(_PARENT) not in sys.path:
        sys.path.insert(0, str(_PARENT))

from newsnow_neon_app.application import AINewsApp, configure_app_services
from newsnow_neon_app.cache import (
    clear_cached_headlines,
    collect_redis_statistics,
    get_cached_article_summary,
    get_redis_client,
    load_cached_headlines,
    load_historical_snapshots,
    persist_headlines_with_ticker,
    store_cached_article_summary,
)
from newsnow_neon_app.config import (
    REQUEST_SELECTORS,
    SECTION_CUTOFF_TAGS,
    SECTION_CUTOFF_TOKENS,
    SECTIONS,
    USER_AGENT,
)
from newsnow_neon_app.http_client import get_http_session, set_retry_statuses
from newsnow_neon_app.main import APP_METADATA, APP_VERSION
from newsnow_neon_app.models import (
    ArticleContent,
    Headline,
    HistoricalSnapshot,
    NewsSection,
    RedisStatistics,
    SummaryResolution,
)
from newsnow_neon_app.utils import (
    compute_deadline_timeout as _compute_deadline_timeout,
    isoformat_epoch as _isoformat_epoch,
    parse_iso8601_utc as _parse_iso8601_utc,
)
from newsnow_neon_app.summaries import summarize_article

try:
    from dotenv import load_dotenv as _load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    _load_dotenv = None
else:
    _load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = True

HTTP_TIMEOUT = 15
HEADLINE_LIMIT: Optional[int] = None
ARTICLE_TIMEOUT = 20
try:
    SUMMARY_TIMEOUT = max(5, int(os.getenv("NEWS_SUMMARY_TIMEOUT", "15")))
except ValueError:
    SUMMARY_TIMEOUT = 15

try:
    ARTICLE_TOTAL_TIMEOUT = max(
        ARTICLE_TIMEOUT,
        int(os.getenv("NEWS_ARTICLE_TOTAL_TIMEOUT", "45")),
    )
except ValueError:
    ARTICLE_TOTAL_TIMEOUT = max(ARTICLE_TIMEOUT, 45)

try:
    TICKER_TIMEOUT = max(3, int(os.getenv("NEWS_TICKER_TIMEOUT", "8")))
except ValueError:
    TICKER_TIMEOUT = 8

BACKGROUND_WATCH_INTERVAL_SECONDS = 90
BACKGROUND_WATCH_INTERVAL_MS = BACKGROUND_WATCH_INTERVAL_SECONDS * 1000
BACKGROUND_WATCH_INITIAL_DELAY_MS = 15_000

ARTICLE_FETCH_RETRY_STATUSES: set[int] = {401, 403, 404, 408, 409, 429, 500, 502, 503}
FALLBACK_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0"
)

set_retry_statuses(ARTICLE_FETCH_RETRY_STATUSES)



def _locate_section_container(soup: BeautifulSoup) -> Tag:
    """Return the DOM node that contains primary headline listings."""
    for selector in ("#newsfeed", "div.newsfeed", "main", "#main", "body"):
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            return node
    return soup



def _iter_section_anchors(container: Tag) -> Iterable[Tag]:
    """Yield anchor nodes within the primary section until the cutoff marker."""
    candidate_ids = {
        id(tag)
        for selector in REQUEST_SELECTORS
        for tag in container.select(selector)
        if isinstance(tag, Tag)
    }
    restrict_to_candidates = bool(candidate_ids)

    for node in container.descendants:
        if isinstance(node, NavigableString):
            normalized = node.strip().lower()
            if normalized and any(token in normalized for token in SECTION_CUTOFF_TOKENS):
                break
            continue

        if not isinstance(node, Tag):
            continue

        if node.name in SECTION_CUTOFF_TAGS:
            snippet = node.get_text(" ", strip=True).lower()
            if snippet and any(token in snippet for token in SECTION_CUTOFF_TOKENS):
                break

        if node.name != "a":
            continue

        if restrict_to_candidates and id(node) not in candidate_ids:
            continue

        yield node


def _extract_article_text_from_soup(soup: BeautifulSoup) -> str:
    candidate_selectors = [
        "article",
        "[role='main'] article",
        "[role='main']",
        ".article",
        ".post",
        ".story",
    ]

    def extract_from(node: Tag) -> str:
        paragraphs = []
        for element in node.find_all(["p", "li"]):
            text = element.get_text(" ", strip=True)
            if len(text.split()) >= 5:
                paragraphs.append(text)
        return "\n\n".join(paragraphs)

    for selector in candidate_selectors:
        node = soup.select_one(selector)
        if node:
            content = extract_from(node)
            if len(content.split()) > 60:
                return content

    paragraphs = []
    for element in soup.find_all("p"):
        text = element.get_text(" ", strip=True)
        if len(text.split()) >= 5:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def fetch_article_content(url: str) -> ArticleContent:
    """Return extracted article text and the resolved final URL for the given link."""
    article = _robust_fetch_article_content(url)
    if article is None:
        raise RuntimeError(f"Unable to fetch article content for {url} after retries.")
    return article


def _robust_fetch_article_content(url: str) -> Optional[ArticleContent]:
    """Attempt to fetch article content with multiple header/URL strategies."""
    session = get_http_session()
    deadline = time.monotonic() + ARTICLE_TOTAL_TIMEOUT
    resolved_url = _resolve_final_url(url, timeout=ARTICLE_TIMEOUT, deadline=deadline)
    attempts: List[tuple[str, str, Dict[str, str]]] = []
    base_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if resolved_url:
        attempts.append(("resolved", resolved_url, base_headers))
        attempts.append(
            (
                "resolved_with_referer",
                resolved_url,
                {**base_headers, "Referer": url},
            )
        )
    attempts.append(("original", url, base_headers))
    attempts.append(
        (
            "original_alt_agent",
            url,
            {**base_headers, "User-Agent": FALLBACK_USER_AGENT, "Referer": url},
        )
    )

    errors: List[str] = []
    for label, target_url, headers in attempts:
        timeout = _compute_deadline_timeout(deadline, ARTICLE_TIMEOUT)
        if timeout is None:
            errors.append("deadline:expired")
            break
        try:
            response = session.get(
                target_url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
            )
            status_code = response.status_code
            if status_code in ARTICLE_FETCH_RETRY_STATUSES:
                errors.append(f"{label}:{status_code}")
                logger.debug(
                    "Retryable status %s when fetching article (%s -> %s)",
                    status_code,
                    url,
                    target_url,
                )
                continue
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            content = _extract_article_text_from_soup(soup).strip()
            if not content:
                errors.append(f"{label}:empty")
                logger.debug("Empty article content after parsing %s", target_url)
                continue
            final_url = response.url or target_url
            return ArticleContent(url=final_url, text=content)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            errors.append(f"{label}:{status}")
            logger.debug(
                "HTTP error during article fetch (%s -> %s): %s",
                url,
                target_url,
                exc,
            )
            continue
        except requests.RequestException as exc:
            errors.append(f"{label}:{exc.__class__.__name__}")
            logger.debug(
                "Network error during article fetch (%s -> %s): %s",
                url,
                target_url,
                exc,
            )
            continue

    if errors:
        logger.warning(
            "Exhausted article fetch attempts for %s (%s)", url, "; ".join(errors)
        )
    return None


def _fallback_summary_from_headline(headline: Headline, article_text: Optional[str]) -> str:
    if article_text:
        fallback = "\n\n".join(article_text.splitlines()[:4])
        if len(fallback) > 800:
            fallback = fallback[:800].rstrip() + "…"
        return fallback or headline.title
    return (
        f"{headline.title}\n\n"
        "Summary unavailable right now. Open the full article for details."
    )


def resolve_article_summary(headline: Headline) -> SummaryResolution:
    """Return a summary for the headline, applying cache lookups and fetch retries."""
    cached_summary = get_cached_article_summary(headline.url, headline.title)
    if cached_summary:
        logger.info("Using cached summary for %s", headline.url)
        return SummaryResolution(
            summary=cached_summary,
            article_text=None,
            from_cache=True,
            source_url=headline.url,
        )

    article = _robust_fetch_article_content(headline.url)
    if article is None:
        fallback = _fallback_summary_from_headline(headline, None)
        logger.info(
            "Falling back to headline-only summary for %s after fetch failures",
            headline.url,
        )
        return SummaryResolution(
            summary=fallback,
            article_text=None,
            from_cache=False,
            source_url=None,
            issue="article_fetch_failed",
        )

    cached_final = get_cached_article_summary(article.url, headline.title)
    if cached_final:
        logger.info(
            "Using cached summary for resolved URL %s (requested %s)",
            article.url,
            headline.url,
        )
        store_cached_article_summary(headline.url, article.url, headline.title, cached_final)
        return SummaryResolution(
            summary=cached_final,
            article_text=article.text,
            from_cache=True,
            source_url=article.url,
        )

    summary_text = summarize_article(headline.title, article.text)
    if summary_text.strip():
        store_cached_article_summary(headline.url, article.url, headline.title, summary_text)
        return SummaryResolution(
            summary=summary_text,
            article_text=article.text,
            from_cache=False,
            source_url=article.url,
        )

    fallback = _fallback_summary_from_headline(headline, article.text)
    return SummaryResolution(
        summary=fallback,
        article_text=article.text,
        from_cache=False,
        source_url=article.url,
        issue="summary_generation_empty",
    )





def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None
def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None
def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None





def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None
def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None





def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None
def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None





def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url



def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None
def _normalize_href(raw: object) -> Optional[str]:
    """Return a string href value if present."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    return str(raw)


def _resolve_final_url(
    url: str,
    *,
    timeout: int = ARTICLE_TIMEOUT,
    deadline: Optional[float] = None,
) -> str:
    """Follow redirects to obtain the final article URL.

    NewsNow uses intermediate pages that immediately redirect via meta refresh.
    We attempt a HEAD request first to preserve bandwidth, falling back to GET
    when necessary, and inspect HTML meta refresh tags if no HTTP redirect is
    provided.
    """
    session = get_http_session()

    head_timeout = _compute_deadline_timeout(deadline, timeout)
    if head_timeout is not None:
        try:
            head_response = session.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=head_timeout,
            )
            if head_response.history:
                return head_response.url
            if head_response.status_code in (301, 302, 303, 307, 308):
                location = head_response.headers.get("Location")
                if location:
                    return urljoin(url, location)
        except Exception as exc:
            logger.debug("HEAD request failed for %s: %s", url, exc)
    else:
        logger.debug("HEAD request skipped for %s; deadline exhausted.", url)

    get_timeout = _compute_deadline_timeout(deadline, timeout)
    if get_timeout is None:
        return url

    try:
        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=get_timeout,
        )
    except Exception:
        return url

    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    refresh_tag = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
    if refresh_tag:
        content = refresh_tag.get("content", "")
        if "url=" in content.lower():
            target = content.split("=", 1)[1].strip()
            if target:
                return urljoin(final_url, target)

    return final_url


def _extract_completion_text(response: Any) -> Optional[str]:
    """Extract textual content from a LiteLLM completion response."""
    choices: Any
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    message: Any
    if isinstance(first, dict):
        message = first.get("message")
    else:
        message = getattr(first, "message", None)

    content = None
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if isinstance(content, str):
        stripped = content.strip()
        return stripped if stripped else None

    if isinstance(content, Sequence):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                if isinstance(text_value, Sequence):
                    parts.extend(str(segment) for segment in text_value)
                    continue
                if "type" in item and isinstance(item.get("type"), str):
                    # Some providers wrap text inside nested keys like output_text/text.
                    for key in ("output_text", "input_text", "content", "value"):
                        nested = item.get(key)
                        if isinstance(nested, str):
                            parts.append(nested)
                            break
                        if isinstance(nested, Sequence):
                            parts.extend(str(segment) for segment in nested)
                            break
        combined = " ".join(part.strip() for part in parts if part and part.strip())
        return combined if combined else None

    return None





    if request_timeout is not None:
        kwargs["timeout"] = request_timeout

    kwargs.setdefault("max_retries", 0)

    def _apply_common(api_base_env: Optional[str]) -> None:
        if api_base_env:
            kwargs["api_base"] = api_base_env.rstrip("/")

    azure_configured = False
    if provider == "azure" or (model and model.startswith("azure/")):
        deployment = azure_deployment_override or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not deployment and model:
            deployment = model.split("/", 1)[1] if model.startswith("azure/") else model

        if deployment:
            kwargs["model"] = f"azure/{deployment}"
            _apply_common(
                api_base_override
                or os.getenv("AZURE_OPENAI_API_BASE")
                or os.getenv("LITELLM_API_BASE")
            )

            api_version = azure_api_version_override or os.getenv("AZURE_OPENAI_API_VERSION")
            kwargs["api_version"] = api_version or "2024-10-01-preview"

            azure_ad_token = azure_ad_token_override or os.getenv("AZURE_OPENAI_AD_TOKEN")
            if azure_ad_token:
                kwargs["azure_ad_token"] = azure_ad_token

            api_key = api_key_override or os.getenv("AZURE_OPENAI_API_KEY")
            if api_key:
                kwargs["api_key"] = api_key

            requested_tokens = kwargs.pop("max_tokens", None)
            if requested_tokens:
                kwargs["max_completion_tokens"] = requested_tokens
                logger.debug(
                    "Mapped max_tokens=%s to max_completion_tokens for Azure.",
                    requested_tokens,
                )

            azure_configured = True
            logger.debug(
                "LiteLLM configured for Azure deployment '%s' (model=%s).",
                deployment,
                kwargs["model"],
            )
        else:
            logger.warning(
                "Azure provider selected but AZURE_OPENAI_DEPLOYMENT/LITELLM_MODEL not configured; "
                "falling back to OpenAI defaults."
            )
            provider = "openai"

    if not azure_configured:
        _apply_common(api_base_override or os.getenv("LITELLM_API_BASE"))
        if model and model.startswith("azure/"):
            kwargs["model"] = model.split("/", 1)[1]
        kwargs["model"] = kwargs.get("model") or "gpt-4.1"
        api_key = api_key_override or os.getenv("LITELLM_API_KEY")
        if api_key:
            kwargs["api_key"] = api_key

    final_model = kwargs.get("model", "")
    normalized_model = final_model.split("/", 1)[-1].lower()
    if normalized_model.startswith("gpt-5"):
        adapted_messages: List[Dict[str, Any]] = []
        for message in kwargs["messages"]:
            updated = dict(message)
            content = updated.get("content")
            if isinstance(content, str):
                updated["content"] = [{"type": "text", "text": content}]
            elif isinstance(content, Sequence):
                new_parts = []
                for part in content:
                    if isinstance(part, str):
                        new_parts.append({"type": "text", "text": part})
                    elif isinstance(part, dict) and "type" in part:
                        new_parts.append(part)
                    else:
                        new_parts.append({"type": "text", "text": str(part)})
                updated["content"] = new_parts
            adapted_messages.append(updated)
        kwargs["messages"] = adapted_messages

    if normalized_model.startswith(("gpt-5-mini", "gpt5-mini")):
        if "temperature" in kwargs:
            kwargs.pop("temperature", None)
            logger.debug("Dropping temperature for %s; not supported.", final_model)
        if "stop" in kwargs:
            kwargs.pop("stop", None)
            logger.debug("Dropping stop parameter for %s; not supported.", final_model)

    # Remove empty/None entries to avoid LiteLLM warnings
    return {key: value for key, value in kwargs.items() if value is not None}


def _fetch_section_headlines(
    section: NewsSection,
    max_items: Optional[int],
    seen: set[tuple[str, str]],
) -> List[Headline]:
    """Fetch headlines for a single NewsNow section.

    When `max_items` is ``None`` the scraper gathers every matching headline.
    """
    logger.debug("Fetching section '%s' (%s)", section.label, section.url)
    headers = {"User-Agent": USER_AGENT}
    session = get_http_session()
    response = session.get(section.url, headers=headers, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    headlines: List[Headline] = []

    def try_add(anchor: Tag) -> None:
        title = anchor.get_text(strip=True)
        href = _normalize_href(anchor.get("href"))
        if not title or not href or href.startswith("#"):
            return
        full_url = urljoin(section.url, href)
        key = (title.lower(), full_url)
        if key in seen or len(title.split()) < 3:
            return

        source_name: Optional[str] = None
        published_label: Optional[str] = None
        published_iso: Optional[str] = None

        meta_container: Optional[Tag] = None
        parent = anchor.parent
        if isinstance(parent, Tag):
            meta_container = parent.find("span", class_="meta")
        if meta_container is None:
            meta_container = anchor.find_next_sibling("span", class_="meta")

        if isinstance(meta_container, Tag):
            source_node = meta_container.select_one(".src")
            if isinstance(source_node, Tag):
                source_name = source_node.get_text(" ", strip=True) or None

            time_node = meta_container.select_one(".time")
            if isinstance(time_node, Tag):
                published_label = time_node.get_text(strip=True) or None
                data_time = time_node.get("data-time")
                if isinstance(data_time, str):
                    published_iso = _isoformat_epoch(data_time)

        if source_name is None or published_label is None or published_iso is None:
            wrapper: Optional[Tag] = None
            for ancestor in anchor.parents:
                if not isinstance(ancestor, Tag):
                    continue
                classes = ancestor.get("class", [])
                if isinstance(classes, str):
                    classes = [classes]
                if "article-card__content-wrapper" in classes:
                    wrapper = ancestor
                    break

            if wrapper is not None:
                lockup = wrapper.find("span", class_="article-card__lockup")
                if isinstance(lockup, Tag):
                    if source_name is None:
                        publisher_node = lockup.select_one(".article-publisher__name")
                        if isinstance(publisher_node, Tag):
                            text = publisher_node.get_text(" ", strip=True)
                            if text:
                                source_name = text

                    if published_label is None or published_iso is None:
                        timestamp_node = lockup.select_one(".article-publisher__timestamp")
                        if isinstance(timestamp_node, Tag):
                            if published_label is None:
                                text = timestamp_node.get_text(strip=True)
                                if text:
                                    published_label = text
                            if published_iso is None:
                                stamp = timestamp_node.get("data-timestamp")
                                if isinstance(stamp, str):
                                    iso_candidate = _isoformat_epoch(stamp)
                                    if iso_candidate:
                                        published_iso = iso_candidate

        headlines.append(
            Headline(
                title=title,
                url=full_url,
                section=section.label,
                source=source_name,
                published_time=published_label,
                published_at=published_iso,
            )
        )
        seen.add(key)

    container = _locate_section_container(soup)
    for anchor in _iter_section_anchors(container):
        try_add(anchor)
        if max_items is not None and len(headlines) >= max_items:
            return headlines

    logger.debug(
        "Section '%s' provided %s headlines (requested %s).",
        section.label,
        len(headlines),
        max_items if max_items is not None else "no limit",
    )
    return headlines


def fetch_headlines(
    max_items: Optional[int] = HEADLINE_LIMIT, *, force_refresh: bool = False
) -> tuple[List[Headline], bool, Optional[str]]:
    """Fetch headlines from multiple NewsNow sections and interleave them.

    Args:
        max_items: Optional limit for the number of headlines to return. ``None``
            (the default) returns every available headline.
        force_refresh: Skip the cache when ``True``.

    Returns:
        A tuple of the interleaved headlines, whether they were loaded from
        cache, and a cached ticker summary when available.
    """
    if max_items is not None and max_items <= 0:
        return [], False, None

    if not force_refresh:
        cached_bundle = load_cached_headlines(max_items)
        if cached_bundle:
            logger.info(
                "Loaded %s cached headlines from Redis.",
                len(cached_bundle.headlines),
            )
            return cached_bundle.headlines, True, cached_bundle.ticker_text

    if max_items is None:
        per_section: Optional[int] = None
    else:
        per_section = max(1, math.ceil(max_items / max(1, len(SECTIONS))))
    seen: set[tuple[str, str]] = set()
    section_results: List[List[Headline]] = []

    for section in SECTIONS:
        try:
            entries = _fetch_section_headlines(
                section, per_section, seen
            )
        except Exception as exc:  # pragma: no cover - network failure
            logger.warning(
                "Failed to fetch section '%s' (%s): %s", section.label, section.url, exc
            )
            continue
        if entries:
            section_results.append(entries)

    if not section_results:
        return [], False, None

    mixed: List[Headline] = []
    seen_keys: set[tuple[str, str]] = set()
    index = 0
    while any(index < len(entries) for entries in section_results):
        if max_items is not None and len(mixed) >= max_items:
            break
        for entries in section_results:
            if index < len(entries):
                candidate = entries[index]
                key = (candidate.title.lower(), candidate.url)
                if key in seen_keys:
                    continue
                mixed.append(candidate)
                seen_keys.add(key)
                if max_items is not None and len(mixed) >= max_items:
                    break
        index += 1

    if mixed:
        return mixed, False, None

    fallback_bundle = load_cached_headlines(max_items)
    if fallback_bundle:
        logger.info("Falling back to cached headlines after empty scrape result.")
        return fallback_bundle.headlines, True, fallback_bundle.ticker_text

    return [], False, None


def build_ticker_text(headlines: Sequence[Headline]) -> str:
    """Construct the ticker line by concatenating headline titles within a limit."""
    if not headlines:
        return "No headlines available right now."

    max_chars = 180
    parts: List[str] = []
    for item in headlines:
        title = item.title.strip()
        if not title:
            continue
        segment = f"[{item.section}] {title}" if item.section else title
        prospective = segment if not parts else " | ".join((*parts, segment))
        if len(prospective) > max_chars:
            if not parts:
                truncated = segment[: max_chars - 1].rstrip()
                parts.append(truncated + "…")
            break
        parts.append(segment)
    if not parts:
        return "No headlines available right now."
    return " | ".join(parts)





configure_app_services(
    fetch_headlines=fetch_headlines,
    build_ticker_text=build_ticker_text,
    resolve_article_summary=resolve_article_summary,
    persist_headlines_with_ticker=persist_headlines_with_ticker,
    collect_redis_statistics=collect_redis_statistics,
    clear_cached_headlines=clear_cached_headlines,
    load_historical_snapshots=load_historical_snapshots,
)


if __name__ == "__main__":
    from newsnow_neon_app.main import main as _run_app_main

    _run_app_main()
