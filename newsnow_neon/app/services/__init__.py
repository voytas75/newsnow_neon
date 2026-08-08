"""Configured application-service exports for NewsNow Neon.

This package is the active import surface for ``newsnow_neon.app.services``.
Its public functions are stable dispatch proxies: callers may import them before
startup configures the concrete legacy implementations.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from ...models import Headline, HistoricalSnapshot, RedisStatistics

FetchHeadlinesImpl = Callable[..., tuple[list[Headline], bool, str | None]]
BuildTickerTextImpl = Callable[[Sequence[Headline]], str]
ResolveArticleSummaryImpl = Callable[[Headline], Any]
PersistHeadlinesImpl = Callable[..., None]
CollectRedisStatisticsImpl = Callable[[], RedisStatistics]
ClearCachedHeadlinesImpl = Callable[[], tuple[bool, str]]
LoadHistoricalSnapshotsImpl = Callable[..., list[HistoricalSnapshot]]


_fetch_headlines_impl: FetchHeadlinesImpl | None = None
_build_ticker_text_impl: BuildTickerTextImpl | None = None
_resolve_article_summary_impl: ResolveArticleSummaryImpl | None = None
_persist_headlines_with_ticker_impl: PersistHeadlinesImpl | None = None
_collect_redis_statistics_impl: CollectRedisStatisticsImpl | None = None
_clear_cached_headlines_impl: ClearCachedHeadlinesImpl | None = None
_load_historical_snapshots_impl: LoadHistoricalSnapshotsImpl | None = None


def configure_app_services(
    *,
    fetch_headlines: FetchHeadlinesImpl,
    build_ticker_text: BuildTickerTextImpl,
    resolve_article_summary: ResolveArticleSummaryImpl,
    persist_headlines_with_ticker: PersistHeadlinesImpl,
    collect_redis_statistics: CollectRedisStatisticsImpl,
    clear_cached_headlines: ClearCachedHeadlinesImpl,
    load_historical_snapshots: LoadHistoricalSnapshotsImpl,
) -> None:
    """Configure concrete implementations without replacing public proxies."""
    global _fetch_headlines_impl
    global _build_ticker_text_impl
    global _resolve_article_summary_impl
    global _persist_headlines_with_ticker_impl
    global _collect_redis_statistics_impl
    global _clear_cached_headlines_impl
    global _load_historical_snapshots_impl

    _fetch_headlines_impl = fetch_headlines
    _build_ticker_text_impl = build_ticker_text
    _resolve_article_summary_impl = resolve_article_summary
    _persist_headlines_with_ticker_impl = persist_headlines_with_ticker
    _collect_redis_statistics_impl = collect_redis_statistics
    _clear_cached_headlines_impl = clear_cached_headlines
    _load_historical_snapshots_impl = load_historical_snapshots


def fetch_headlines(
    *args: Any,
    **kwargs: Any,
) -> tuple[list[Headline], bool, str | None]:
    """Fetch headlines through the configured implementation."""
    if _fetch_headlines_impl is None:
        raise RuntimeError("fetch_headlines service not configured")
    return _fetch_headlines_impl(*args, **kwargs)


def build_ticker_text(headlines: Sequence[Headline]) -> str:
    """Build ticker text through the configured implementation."""
    if _build_ticker_text_impl is None:
        raise RuntimeError("build_ticker_text service not configured")
    return _build_ticker_text_impl(headlines)


def resolve_article_summary(headline: Headline) -> Any:
    """Resolve an article summary through the configured implementation."""
    if _resolve_article_summary_impl is None:
        raise RuntimeError("resolve_article_summary service not configured")
    return _resolve_article_summary_impl(headline)


def persist_headlines_with_ticker(*args: Any, **kwargs: Any) -> None:
    """Persist headlines through the configured implementation."""
    if _persist_headlines_with_ticker_impl is None:
        raise RuntimeError("persist_headlines_with_ticker service not configured")
    _persist_headlines_with_ticker_impl(*args, **kwargs)


def collect_redis_statistics() -> RedisStatistics:
    """Collect Redis statistics through the configured implementation."""
    if _collect_redis_statistics_impl is None:
        raise RuntimeError("collect_redis_statistics service not configured")
    return _collect_redis_statistics_impl()


def clear_cached_headlines() -> tuple[bool, str]:
    """Clear cached headlines through the configured implementation."""
    if _clear_cached_headlines_impl is None:
        raise RuntimeError("clear_cached_headlines service not configured")
    return _clear_cached_headlines_impl()


def load_historical_snapshots(
    *args: Any,
    **kwargs: Any,
) -> list[HistoricalSnapshot]:
    """Load snapshots through the configured implementation."""
    if _load_historical_snapshots_impl is None:
        raise RuntimeError("load_historical_snapshots service not configured")
    return _load_historical_snapshots_impl(*args, **kwargs)


__all__ = [
    "configure_app_services",
    "fetch_headlines",
    "build_ticker_text",
    "resolve_article_summary",
    "persist_headlines_with_ticker",
    "collect_redis_statistics",
    "clear_cached_headlines",
    "load_historical_snapshots",
]
