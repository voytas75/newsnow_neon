"""Service injection and proxy layer for NewsNow Neon app.

Updates: v0.52 - 2025-11-18 - Extracted service bindings from application
controller.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence, Tuple

from ..models import Headline, HistoricalSnapshot, RedisStatistics


_fetch_headlines_impl: Optional[
    Callable[..., Tuple[List[Headline], bool, Optional[str]]]
] = None
_build_ticker_text_impl: Optional[Callable[[Sequence[Headline]], str]] = None
_resolve_article_summary_impl: Optional[Callable[[Headline], Any]] = None
_persist_headlines_with_ticker_impl: Optional[Callable[..., None]] = None
_collect_redis_statistics_impl: Optional[Callable[[], RedisStatistics]] = None
_clear_cached_headlines_impl: Optional[Callable[[], Tuple[bool, str]]] = None
_load_historical_snapshots_impl: Optional[
    Callable[..., List[HistoricalSnapshot]]
] = None


def configure_app_services(
    *,
    fetch_headlines: Callable[..., Tuple[List[Headline], bool, Optional[str]]],
    build_ticker_text: Callable[[Sequence[Headline]], str],
    resolve_article_summary: Callable[[Headline], Any],
    persist_headlines_with_ticker: Callable[..., None],
    collect_redis_statistics: Callable[[], RedisStatistics],
    clear_cached_headlines: Callable[[], Tuple[bool, str]],
    load_historical_snapshots: Callable[..., List[HistoricalSnapshot]],
) -> None:
    """Bind concrete service implementations for the application controller.

    This keeps behavior identical to the previous globals while providing a
    single import location for the controller to call through.
    """
    global _fetch_headlines_impl, _build_ticker_text_impl
    global _resolve_article_summary_impl, _persist_headlines_with_ticker_impl
    global _collect_redis_statistics_impl, _clear_cached_headlines_impl
    global _load_historical_snapshots_impl

    _fetch_headlines_impl = fetch_headlines
    _build_ticker_text_impl = build_ticker_text
    _resolve_article_summary_impl = resolve_article_summary
    _persist_headlines_with_ticker_impl = persist_headlines_with_ticker
    _collect_redis_statistics_impl = collect_redis_statistics
    _clear_cached_headlines_impl = clear_cached_headlines
    _load_historical_snapshots_impl = load_historical_snapshots


def fetch_headlines(*args: Any, **kwargs: Any) -> Tuple[List[Headline], bool, Optional[str]]:
    """Proxy to the configured 'fetch_headlines' implementation."""
    if _fetch_headlines_impl is None:
        raise RuntimeError("fetch_headlines service not configured")
    return _fetch_headlines_impl(*args, **kwargs)


def build_ticker_text(headlines: Sequence[Headline]) -> str:
    """Proxy to the configured 'build_ticker_text' implementation."""
    if _build_ticker_text_impl is None:
        raise RuntimeError("build_ticker_text service not configured")
    return _build_ticker_text_impl(headlines)


def resolve_article_summary(headline: Headline) -> Any:
    """Proxy to the configured 'resolve_article_summary' implementation."""
    if _resolve_article_summary_impl is None:
        raise RuntimeError("resolve_article_summary service not configured")
    return _resolve_article_summary_impl(headline)


def persist_headlines_with_ticker(*args: Any, **kwargs: Any) -> None:
    """Proxy to the configured 'persist_headlines_with_ticker' implementation."""
    if _persist_headlines_with_ticker_impl is None:
        raise RuntimeError("persist_headlines_with_ticker service not configured")
    _persist_headlines_with_ticker_impl(*args, **kwargs)


def collect_redis_statistics() -> RedisStatistics:
    """Proxy to the configured 'collect_redis_statistics' implementation."""
    if _collect_redis_statistics_impl is None:
        raise RuntimeError("collect_redis_statistics service not configured")
    return _collect_redis_statistics_impl()


def clear_cached_headlines() -> Tuple[bool, str]:
    """Proxy to the configured 'clear_cached_headlines' implementation."""
    if _clear_cached_headlines_impl is None:
        raise RuntimeError("clear_cached_headlines service not configured")
    return _clear_cached_headlines_impl()


def load_historical_snapshots(*args: Any, **kwargs: Any) -> List[HistoricalSnapshot]:
    """Proxy to the configured 'load_historical_snapshots' implementation."""
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