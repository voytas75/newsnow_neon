"""Regression coverage for the unconfigured cache-service provider."""

from __future__ import annotations

import pytest

from newsnow_neon.app.services import cache_service


def test_unconfigured_cache_service_explains_how_to_configure() -> None:
    """Keep the cache provider stub failure explicit and actionable."""
    with pytest.raises(
        NotImplementedError,
        match="Provide via configure_app_services or implement provider",
    ):
        cache_service.clear_cached_headlines()
