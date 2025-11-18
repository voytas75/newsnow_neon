from __future__ import annotations

"""News service providers for NewsNow Neon.

Updates: v0.60 - 2025-11-18 - Introduced dedicated service provider module
to hold signatures for headline fetching and ticker composition, enabling
modularization while keeping application orchestration minimal.
"""

from typing import List, Optional, Sequence, Tuple

from ...models import Headline


def fetch_headlines(
    *, force_refresh: bool = False
) -> Tuple[List[Headline], bool, Optional[str]]:
    """Fetch headlines tuple (headlines, from_cache, cached_ticker).

    This is a provider stub. Implement this function or inject an
    implementation via [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


def build_ticker_text(headlines: Sequence[Headline]) -> str:
    """Build scroller text for given headlines.

    This is a provider stub. Implement this function or inject an
    implementation via [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


__all__ = ["fetch_headlines", "build_ticker_text"]