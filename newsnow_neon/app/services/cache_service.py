from __future__ import annotations

"""Cache service providers for NewsNow Neon.

Updates: v0.60 - 2025-11-18 - Introduced dedicated cache service module to
host signatures for cache persistence, clearing, and history snapshot loading.
Controllers continue to import through the facade in
[app/services.py](newsnow_neon/app/services.py).
"""

from typing import Any, List, Sequence, Tuple

from ...models import Headline, HistoricalSnapshot


def persist_headlines_with_ticker(
    headlines: Sequence[Headline], ticker_text: str
) -> None:
    """Persist fetched headlines alongside the prepared ticker text.

    Implement this provider or inject a concrete function via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


def clear_cached_headlines() -> Tuple[bool, str]:
    """Clear cached headlines; returns (success, message).

    Implement this provider or inject a concrete function via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


def load_historical_snapshots(*args: Any, **kwargs: Any) -> List[HistoricalSnapshot]:
    """Load last 24h historical snapshots from the cache backend.

    Implement this provider or inject a concrete function via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


__all__ = [
    "persist_headlines_with_ticker",
    "clear_cached_headlines",
    "load_historical_snapshots",
]