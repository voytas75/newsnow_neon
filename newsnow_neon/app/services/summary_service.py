from __future__ import annotations

"""Summary service providers for NewsNow Neon.

Updates: v0.60 - 2025-11-18 - Introduced dedicated service provider module
to hold the headline summary resolution signature, supporting modularization
while keeping application orchestration minimal.
"""

from typing import Any

from ...models import Headline


def resolve_article_summary(headline: Headline) -> Any:
    """Resolve or generate a summary payload for a headline.

    This is a provider stub. Implement this function or inject an
    implementation via [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


__all__ = ["resolve_article_summary"]