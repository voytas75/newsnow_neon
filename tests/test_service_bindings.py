"""Regression coverage for configured application-service bindings."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

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


def test_services_file_wrapper_dispatches_through_configured_package() -> None:
    """A services.py file-path load must use the configured package proxies."""
    service_package = importlib.reload(services)
    service_file = importlib.util.spec_from_file_location(
        "newsnow_neon.app._services_file",
        Path(__file__).resolve().parents[1] / "newsnow_neon" / "app" / "services.py",
    )
    assert service_file is not None and service_file.loader is not None
    service_file_module = importlib.util.module_from_spec(service_file)
    service_file.loader.exec_module(service_file_module)
    direct_fetch = service_file_module.fetch_headlines
    expected_headline = Headline(title="File wrapper", url="https://example.test/file")
    calls: list[bool] = []

    def fetch_headlines(
        *, force_refresh: bool = False
    ) -> tuple[list[Headline], bool, str | None]:
        calls.append(force_refresh)
        return [expected_headline], False, None

    service_package.configure_app_services(
        fetch_headlines=fetch_headlines,
        build_ticker_text=lambda headlines: " | ".join(
            item.title for item in headlines
        ),
        resolve_article_summary=lambda _headline: {"summary": "configured"},
        persist_headlines_with_ticker=lambda *_args, **_kwargs: None,
        collect_redis_statistics=lambda: RedisStatistics(False, False, "cache", False),
        clear_cached_headlines=lambda: (True, "ok"),
        load_historical_snapshots=lambda *_args, **_kwargs: [],
    )

    assert direct_fetch(force_refresh=True) == ([expected_headline], False, None)
    assert service_file_module.fetch_headlines() == ([expected_headline], False, None)
    assert calls == [True, False]
