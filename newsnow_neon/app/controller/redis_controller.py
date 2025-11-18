"""Redis diagnostics controller.

Updates: v0.52 - 2025-11-18 - Minimal wrapper for meter updates.
"""
from __future__ import annotations


class RedisController:
    """Delegates Redis meter update to the application."""

    def __init__(self, app) -> None:
        self.app = app

    def update_redis_meter(self) -> None:
        self.app._update_redis_meter()
