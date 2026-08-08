"""Regression coverage for configured application-service bindings."""

from __future__ import annotations

import importlib

from newsnow_neon.app import services
from newsnow_neon.models import Headline, RedisStatistics


def test_direct_service_import_remains_live_after_configuration() -> None:
    """A callable imported before configuration must dispatch after configuration."""
    service_module = importlib.reload(services)
    direct_fetch = service_module.fetch_headlines
    expected_headline = Headline(title="Configured", url="https://example.test/article")
    calls: list[bool] = []

    def fetch_headlines(
        *, force_refresh: bool = False
    ) -> tuple[list[Headline], bool, str | None]:
        calls.append(force_refresh)
        return [expected_headline], False, None

    def build_ticker_text(headlines: list[Headline]) -> str:
        return " | ".join(item.title for item in headlines)

    def resolve_article_summary(_headline: Headline) -> object:
        return {"summary": "configured"}

    def persist_headlines_with_ticker(*_args: object, **_kwargs: object) -> None:
        return None

    def collect_redis_statistics() -> RedisStatistics:
        return RedisStatistics(False, False, "cache", False)

    def clear_cached_headlines() -> tuple[bool, str]:
        return True, "ok"

    def load_historical_snapshots(*_args: object, **_kwargs: object) -> list[object]:
        return []

    service_module.configure_app_services(
        fetch_headlines=fetch_headlines,
        build_ticker_text=build_ticker_text,
        resolve_article_summary=resolve_article_summary,
        persist_headlines_with_ticker=persist_headlines_with_ticker,
        collect_redis_statistics=collect_redis_statistics,
        clear_cached_headlines=clear_cached_headlines,
        load_historical_snapshots=load_historical_snapshots,
    )

    assert direct_fetch(force_refresh=True) == ([expected_headline], False, None)
    assert service_module.fetch_headlines() == ([expected_headline], False, None)
    assert calls == [True, False]
