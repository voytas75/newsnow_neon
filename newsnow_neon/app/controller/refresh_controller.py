"""Refresh controller: encapsulates headline fetch lifecycle.

Updates: v0.60 - 2025-11-18 - Extracted refresh workflow from the monolithic
AINewsApp into a modular controller with service injection.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import List, Optional

from ..models import Headline
from ..app.services import (
    fetch_headlines,
    build_ticker_text,
    persist_headlines_with_ticker,
)

logger = logging.getLogger(__name__)


class RefreshController:
    """Manage refresh lifecycle and delegate UI updates to the app.

    This controller moves the headline fetching thread, error handling,
    and success callbacks into a cohesive unit. It calls back into the
    provided app instance to preserve behavior while reducing the
    application module size.

    Responsibilities:
    - Exit history mode before refresh.
    - Update status labels (next refresh, summary).
    - Spawn background worker for network/cache operations.
    - Persist cache payload when needed.
    - Notify the app to render results or handle errors.
    """

    def __init__(self, app: "AINewsApp") -> None:
        """Initialize the controller with a reference to the root app."""
        self.app = app

    def refresh(self, *, force_refresh: bool = False) -> None:
        """Kick off a refresh in a background thread."""
        if getattr(self.app, "_history_mode", False):
            # Use the existing app flow to leave history mode.
            self.app._exit_history_mode(trigger_refresh=False)

        self.app._log_status("Fetching AI headlines…")
        if hasattr(self.app, "next_refresh_var"):
            try:
                self.app.next_refresh_var.set("Refreshing…")
            except Exception:
                logger.debug("Unable to set next refresh label during refresh.")
        self.app._update_status_summary()

        threading.Thread(
            target=self._worker, args=(force_refresh,), daemon=True
        ).start()

    def _worker(self, force_refresh: bool) -> None:
        """Run the fetch workflow in a thread, then callback on the UI thread."""
        logger.info("Refreshing headlines (force_refresh=%s)", force_refresh)
        try:
            fetched_at = datetime.now()
            headlines, from_cache, cached_ticker = fetch_headlines(
                force_refresh=force_refresh
            )
            if from_cache:
                ticker_text = cached_ticker or build_ticker_text(headlines)
                should_update_cache = bool(headlines) and not cached_ticker
            else:
                ticker_text = build_ticker_text(headlines)
                should_update_cache = bool(headlines)

            if should_update_cache:
                persist_headlines_with_ticker(headlines, ticker_text)

        except Exception as exc:
            logger.exception("Failed to update headlines:")
            # Schedule UI error handling on the main thread.
            self.app.after(0, lambda: self._handle_error(exc))
            return

        # Schedule UI success handling on the main thread.
        self.app.after(
            0,
            lambda: self._handle_result(
                headlines=headlines,
                ticker_text=ticker_text,
                from_cache=from_cache,
                fetched_at=fetched_at,
            ),
        )

    def _handle_result(
        self,
        *,
        headlines: List[Headline],
        ticker_text: str,
        from_cache: bool,
        fetched_at: datetime,
    ) -> None:
        """Forward successful refresh result to the app's renderer."""
        # Preserve app-side state updates and rendering path.
        self.app._handle_refresh_result(
            headlines=headlines,
            ticker_text=ticker_text,
            from_cache=from_cache,
            fetched_at=fetched_at,
        )

    def _handle_error(self, exc: Exception) -> None:
        """Forward fetch errors to the app's existing error handler."""
        self.app._handle_fetch_error(exc)


__all__ = ["RefreshController"]