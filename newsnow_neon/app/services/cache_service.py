"""Cache service providers for NewsNow Neon.

Updates: v0.60 - 2025-11-18 - Introduced dedicated Cache service module to host
cache maintenance signatures. Concrete implementations should be injected via
[configure_app_services()](newsnow_neon/app/services.py:22).
"""
from __future__ import annotations

from typing import Tuple


def clear_cached_headlines() -> Tuple[bool, str]:
    """Clear cached headlines; returns (success, message).

    Provide a concrete implementation via
    [configure_app_services()](newsnow_neon/app/services.py:22).
    """
    raise NotImplementedError(
        "Provide via configure_app_services or implement provider"
    )


__all__ = ["clear_cached_headlines"]