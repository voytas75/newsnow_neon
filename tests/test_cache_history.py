"""Offline regression coverage for cache-history payload handling."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from newsnow_neon import cache
from newsnow_neon.models import Headline, HeadlineCache


class _FakeRedis:
    """In-memory Redis subset used by the historical snapshot reader."""

    def __init__(self, payloads: dict[str, str]) -> None:
        self.payloads = payloads
        self.get_calls: list[str] = []

    def scan_iter(self, *, match: str) -> list[str]:
        """Return configured history keys without contacting Redis."""
        prefix = match.removesuffix("*")
        return [key for key in self.payloads if key.startswith(prefix)]

    def get(self, key: str) -> str | None:
        """Return the configured payload and record the lookup."""
        self.get_calls.append(key)
        return self.payloads.get(key)


def _payload(title: str) -> str:
    """Build a valid cache payload with one deterministic headline."""
    bundle = HeadlineCache(
        headlines=[Headline(title=title, url=f"https://example.test/{title}")],
        ticker_text=f"Ticker: {title}",
        summaries={"https://example.test/article": "Cached summary"},
    )
    return json.dumps(bundle.to_payload())


def test_load_historical_snapshots_returns_no_entries_for_zero_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A zero history limit must not read or return a snapshot."""
    client = _FakeRedis({"news:2026-08-08:120000": _payload("headline")})
    monkeypatch.setattr(cache, "get_redis_client", lambda: client)

    snapshots = cache.load_historical_snapshots(limit=0, horizon=None)

    assert snapshots == []
    assert client.get_calls == []


def test_load_historical_snapshots_keeps_recent_valid_entries_with_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """History should return only the newest valid snapshot inside the horizon."""
    now = datetime.now(timezone.utc)
    recent = now - timedelta(minutes=5)
    older = now - timedelta(minutes=20)
    stale = now - timedelta(hours=3)
    recent_key = f"news:{recent:%Y-%m-%d:%H%M%S}"
    older_key = f"news:{older:%Y-%m-%d:%H%M%S}"
    stale_key = f"news:{stale:%Y-%m-%d:%H%M%S}"
    client = _FakeRedis(
        {
            recent_key: _payload("recent headline"),
            older_key: _payload("older headline"),
            stale_key: _payload("stale headline"),
            "news:not-a-date:not-a-time": _payload("invalid key"),
            "news:2026-08-08:115959": "{not-json",
        }
    )
    monkeypatch.setattr(cache, "get_redis_client", lambda: client)

    snapshots = cache.load_historical_snapshots(
        limit=1,
        horizon=timedelta(hours=1),
    )

    assert [snapshot.key for snapshot in snapshots] == [recent_key]
    assert snapshots[0].headline_count == 1
    assert snapshots[0].summary_count == 1
    assert stale_key not in client.get_calls


def test_load_cached_headlines_limits_valid_payload_and_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The primary cache should preserve metadata while limiting headlines."""
    client = _FakeRedis({cache.CACHE_KEY: _payload("first headline")})
    monkeypatch.setattr(cache, "get_redis_client", lambda: client)

    cached = cache.load_cached_headlines(max_items=0, require_headlines=False)

    assert cached is not None
    assert cached.headlines == []
    assert cached.ticker_text == "Ticker: first headline"
    assert cached.summaries == {"https://example.test/article": "Cached summary"}

    client.payloads[cache.CACHE_KEY] = "{not-json"

    assert cache.load_cached_headlines(max_items=None) is None
