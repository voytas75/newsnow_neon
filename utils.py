"""Utility helpers shared across NewsNow Neon modules.

The functions here were lifted from the original monolithic script so that both
model code and the eventual orchestration layer can consume them without
dragging in side effects.

Updates: v0.49.1 - 2025-01-07 - Seeded module with environment and timing helpers.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional


def read_optional_env(name: str) -> Optional[str]:
    """Return trimmed environment variable or ``None`` when unset/blank."""

    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def compute_deadline_timeout(deadline: Optional[float], fallback: float) -> Optional[float]:
    """Resolve remaining timeout based on a monotonic deadline."""

    if deadline is None:
        return float(fallback)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    return max(1.0, min(float(fallback), remaining))


def isoformat_epoch(value: str) -> Optional[str]:
    """Return a UTC ISO-8601 string from a NewsNow epoch value when possible."""

    candidate = value.strip()
    if not candidate:
        return None

    try:
        epoch = int(candidate)
    except ValueError:
        return None

    try:
        timestamp = datetime.fromtimestamp(epoch, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None

    iso_value = timestamp.isoformat()
    return iso_value[:-6] + "Z" if iso_value.endswith("+00:00") else iso_value


__all__ = ["read_optional_env", "compute_deadline_timeout", "isoformat_epoch"]
