"""Compatibility exports for file-path consumers of application services.

Normal ``newsnow_neon.app.services`` imports resolve to the package initializer.
When this sibling file is loaded explicitly, it re-exports the same stable
package proxies so pre-configuration imports remain live after startup binds the
concrete implementations.
"""

from __future__ import annotations

from newsnow_neon.app.services import (
    build_ticker_text,
    clear_cached_headlines,
    collect_redis_statistics,
    configure_app_services,
    fetch_headlines,
    load_historical_snapshots,
    persist_headlines_with_ticker,
    resolve_article_summary,
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
