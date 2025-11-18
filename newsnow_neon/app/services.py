from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence, Tuple

from ...models import Headline, HistoricalSnapshot, RedisStatistics


# Module-level service implementations injected at app startup.
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
    """Configure NewsNow Neon application service implementations.

    This enables late binding for I/O bound services so the UI layer stays
    decoupled from concrete implementations (useful for testing and swaps).
    """
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


def fetch_headlines(*args: Any, **kwargs: Any) -> Tuple[List[Headline], bool, Optional[str]]:
    """Fetch headlines tuple (headlines, from_cache, cached_ticker)."""
    if _fetch_headlines_impl is None:
        raise RuntimeError("fetch_headlines service not configured")
    return _fetch_headlines_impl(*args, **kwargs)


def build_ticker_text(headlines: Sequence[Headline]) -> str:
    """Build scroller text for given headlines."""
    if _build_ticker_text_impl is None:
        raise RuntimeError("build_ticker_text service not configured")
    return _build_ticker_text_impl(headlines)


def resolve_article_summary(headline: Headline) -> Any:
    """Resolve or generate a summary payload for a headline."""
    if _resolve_article_summary_impl is None:
        raise RuntimeError("resolve_article_summary service not configured")
    return _resolve_article_summary_impl(headline)


def persist_headlines_with_ticker(*args: Any, **kwargs: Any) -> None:
    """Persist fetched headlines alongside the prepared ticker text."""
    if _persist_headlines_with_ticker_impl is None:
        raise RuntimeError("persist_headlines_with_ticker service not configured")
    _persist_headlines_with_ticker_impl(*args, **kwargs)


def collect_redis_statistics() -> RedisStatistics:
    """Collect Redis cache availability and key diagnostics."""
    if _collect_redis_statistics_impl is None:
        raise RuntimeError("collect_redis_statistics service not configured")
    return _collect_redis_statistics_impl()


def clear_cached_headlines() -> Tuple[bool, str]:
    """Clear cached headlines; returns (success, message)."""
    if _clear_cached_headlines_impl is None:
        raise RuntimeError("clear_cached_headlines service not configured")
    return _clear_cached_headlines_impl()


def load_historical_snapshots(*args: Any, **kwargs: Any) -> List[HistoricalSnapshot]:
    """Load last 24h historical snapshots from the cache backend."""
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