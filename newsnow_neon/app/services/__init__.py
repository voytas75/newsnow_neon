"""Modular service-provider package exports for NewsNowNeon.

This package exists so submodules like `news_service` and `summary_service`
are real importable surfaces rather than dead scaffolding behind
`newsnow_neon.app.services.py`.
"""

from .cache_service import clear_cached_headlines
from .news_service import (
    build_ticker_text,
    fetch_headlines,
    load_historical_snapshots,
    persist_headlines_with_ticker,
)
from .redis_service import collect_redis_statistics
from .summary_service import resolve_article_summary


def configure_app_services(
    *,
    fetch_headlines,
    build_ticker_text,
    resolve_article_summary,
    persist_headlines_with_ticker,
    collect_redis_statistics,
    clear_cached_headlines,
    load_historical_snapshots,
) -> None:
    """Configure package-level service exports by rebinding the public callables."""
    globals().update(
        {
            "fetch_headlines": fetch_headlines,
            "build_ticker_text": build_ticker_text,
            "resolve_article_summary": resolve_article_summary,
            "persist_headlines_with_ticker": persist_headlines_with_ticker,
            "collect_redis_statistics": collect_redis_statistics,
            "clear_cached_headlines": clear_cached_headlines,
            "load_historical_snapshots": load_historical_snapshots,
        }
    )


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
