"""Regression coverage for unconfigured news-service providers."""

from __future__ import annotations

import pytest

from newsnow_neon.app.services import news_service

_NOT_CONFIGURED = "Provide via configure_app_services or implement provider"


def test_unconfigured_news_service_stubs_explain_how_to_configure() -> None:
    """Keep unconfigured provider failures explicit and actionable."""
    with pytest.raises(NotImplementedError, match=_NOT_CONFIGURED):
        news_service.fetch_headlines()
    with pytest.raises(NotImplementedError, match=_NOT_CONFIGURED):
        news_service.build_ticker_text([])
    with pytest.raises(NotImplementedError, match=_NOT_CONFIGURED):
        news_service.persist_headlines_with_ticker()
    with pytest.raises(NotImplementedError, match=_NOT_CONFIGURED):
        news_service.load_historical_snapshots()
