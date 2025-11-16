"""Shared HTTP session management for NewsNow Neon network requests.

Updates: v0.50 - 2025-01-07 - Extracted pooled session helpers from the legacy script.
"""

from __future__ import annotations

import atexit
import threading
from typing import Iterable, Sequence, Set

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

_HTTP_THREAD_LOCAL = threading.local()
_HTTP_SESSION_LOCK = threading.Lock()
_HTTP_SESSIONS: Set[Session] = set()
_RETRY_STATUSES: Set[int] = {
    401,
    403,
    404,
    408,
    409,
    429,
    500,
    502,
    503,
}


def set_retry_statuses(statuses: Iterable[int]) -> None:
    """Override the status codes considered retryable for shared sessions."""

    global _RETRY_STATUSES
    _RETRY_STATUSES = {int(code) for code in statuses}


def _build_retry() -> Retry:
    return Retry(  # pragma: no cover - network configuration
        total=2,
        backoff_factor=0.3,
        status_forcelist=list(_RETRY_STATUSES),
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False,
    )


def get_http_session() -> Session:
    """Return a thread-local shared requests session configured with retries."""

    session = getattr(_HTTP_THREAD_LOCAL, "session", None)
    if session is not None:
        return session
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=4, pool_maxsize=8, max_retries=_build_retry())
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    with _HTTP_SESSION_LOCK:
        _HTTP_SESSIONS.add(session)
    _HTTP_THREAD_LOCAL.session = session
    return session


def close_all_sessions() -> None:
    """Close pooled HTTP sessions at shutdown."""

    with _HTTP_SESSION_LOCK:
        sessions: Sequence[Session] = tuple(_HTTP_SESSIONS)
        _HTTP_SESSIONS.clear()
    for session in sessions:
        try:
            session.close()
        except Exception:  # pragma: no cover - defensive close
            continue


atexit.register(close_all_sessions)


__all__ = ["get_http_session", "set_retry_statuses", "close_all_sessions"]
