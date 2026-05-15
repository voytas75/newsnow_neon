"""Modular service-provider package exports for NewsNowNeon.

This package exists so submodules like `news_service` and `summary_service`
are real importable surfaces rather than dead scaffolding behind
`newsnow_neon.app.services.py`.
"""


from .cache_service import clear_cached_headlines as _clear_cached_headlines_placeholder
from .news_service import (
    build_ticker_text as _build_ticker_text_placeholder,
    fetch_headlines as _fetch_headlines_placeholder,
    load_historical_snapshots as _load_historical_snapshots_placeholder,
    persist_headlines_with_ticker as _persist_headlines_with_ticker_placeholder,
)
from .redis_service import collect_redis_statistics as _collect_redis_statistics_placeholder
from .summary_service import resolve_article_summary as _resolve_article_summary_placeholder

fetch_headlines = _fetch_headlines_placeholder
build_ticker_text = _build_ticker_text_placeholder
resolve_article_summary = _resolve_article_summary_placeholder
persist_headlines_with_ticker = _persist_headlines_with_ticker_placeholder
collect_redis_statistics = _collect_redis_statistics_placeholder
clear_cached_headlines = _clear_cached_headlines_placeholder
load_historical_snapshots = _load_historical_snapshots_placeholder


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
