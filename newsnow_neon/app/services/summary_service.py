"""Summary service providers for NewsNow Neon.

Updates: v0.60 - 2025-11-18 - Introduced dedicated Summary service module to host
summary resolution signature. Concrete implementations should be injected via
[configure_app_services()](newsnow_neon/app/services.py:22).
"""
from __future__ import annotations

from ...models import Headline, SummaryResolution


def resolve_article_summary(_headline: Headline) -> SummaryResolution:
    """Resolve or generate a summary payload for a headline.

    Provide a concrete implementation via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


__all__ = ["resolve_article_summary"]