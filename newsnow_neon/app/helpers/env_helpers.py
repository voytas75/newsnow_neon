"""Environment helper functions for NewsNow Neon.

Updates: v0.53 - 2025-11-18 - Extracted environment sanitization helpers
into a dedicated module to slim down the main application controller.
"""

from __future__ import annotations

import re

_SENSITIVE_ENV_PATTERN = re.compile(
    r"(KEY|TOKEN|SECRET|PASSWORD|API_KEY)$", re.IGNORECASE
)


def sanitize_env_value(name: str, value: str | None) -> str | None:
    """Mask sensitive environment variable values for safe logging.

    Returns:
        - "***" for sensitive keys with a value
        - None for empty values
        - Truncated long values (> 80 chars)
        - Original value otherwise

    """
    if value is None:
        return None
    if _SENSITIVE_ENV_PATTERN.search(name) or any(
        token in name for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")
    ):
        return "***" if value else None
    if len(value) > 80:
        return value[:77] + "…"
    return value


__all__ = ["sanitize_env_value"]
