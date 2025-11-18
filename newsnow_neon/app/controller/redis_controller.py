"""RedisController centralizes Redis meter and diagnostics window workflow.

Updates: v0.52 - 2025-11-18 - Introduce controller scaffold delegating to
AINewsApp methods to preserve current behavior while refactoring; later
iterations can migrate ping/update and window management fully here.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Forward-declare to avoid circular import at runtime.
    from ...application import AINewsApp


logger = logging.getLogger(__name__)


class RedisController:
    """Encapsulates Redis meter updates, diagnostics window, and cache clear."""

    def __init__(self, app: "AINewsApp") -> None:
        """Bind to the Tk application orchestrator instance."""
        self.app = app

    # Public API — UI commands

    def clear_cache(self) -> None:
        """Trigger a background task to clear the Redis headline cache."""
        # Preserve app threading behavior
        self.app.clear_cache()

    def open_redis_stats(self) -> None:
        """Open or refresh the Redis statistics window."""
        self.app._open_redis_stats()

    def update_redis_meter(self) -> None:
        """Ping Redis client and update meter label and button state."""
        self.app._update_redis_meter()

    def on_redis_stats_closed(self) -> None:
        """Handle closing of Redis stats window and restore button state."""
        self.app._on_redis_stats_closed()


__all__ = ["RedisController"]