"""News service providers for NewsNow Neon.

Updates: v0.60 - 2025-11-18 - Introduced dedicated News service module to host
fetch/build/persist/history signatures. Concrete implementations should be
injected via [configure_app_services()](newsnow_neon/app/services.py:22).
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ...models import Headline, HistoricalSnapshot


def fetch_headlines(*_args, **_kwargs) -> Tuple[List[Headline], bool, Optional[str]]:
    """Fetch headlines tuple (headlines, from_cache, cached_ticker).

    Provide a concrete implementation via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


def build_ticker_text(_headlines: Sequence[Headline]) -> str:
    """Build scroller text for given headlines.

    Provide a concrete implementation via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


def persist_headlines_with_ticker(*_args, **_kwargs) -> None:
    """Persist fetched headlines alongside the prepared ticker text.

    Provide a concrete implementation via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


def load_historical_snapshots(*_args, **_kwargs) -> List[HistoricalSnapshot]:
    """Load last 24h historical snapshots from the cache backend.

    Provide a concrete implementation via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


__all__ = [
    "fetch_headlines",
    "build_ticker_text",
    "persist_headlines_with_ticker",
    "load_historical_snapshots",
]