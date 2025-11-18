from __future__ import annotations

"""Redis service providers for NewsNow Neon.

Updates: v0.60 - 2025-11-18 - Introduced dedicated Redis service module to
host diagnostics collection signature. Controllers continue importing through
the facade in [app/services.py](newsnow_neon/app/services.py).
"""

from ...models import RedisStatistics


def collect_redis_statistics() -> RedisStatistics:
    """Collect Redis cache availability and key diagnostics.

    Implement this provider or inject a concrete function via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


__all__ = ["collect_redis_statistics"]