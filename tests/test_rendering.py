"""Regression coverage for headline rendering helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from newsnow_neon.app import rendering
from newsnow_neon.models import Headline


class _FrozenDateTime:
    """Minimal datetime replacement for deterministic grouping tests."""

    @classmethod
    def now(cls, _tz: timezone) -> datetime:
        return datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def test_group_headlines_by_age_orders_nonempty_buckets(monkeypatch) -> None:
    """Group current, recent, and undated headlines in display order."""
    monkeypatch.setattr(rendering, "datetime", _FrozenDateTime)
    entries = [
        (
            0,
            Headline(
                title="Current",
                url="https://example.test/0",
                published_at="2026-08-09T11:58:00+00:00",
            ),
        ),
        (
            1,
            Headline(
                title="Recent",
                url="https://example.test/1",
                published_at="2026-08-09T11:52:00+00:00",
            ),
        ),
        (
            2,
            Headline(
                title="Older",
                url="https://example.test/2",
                published_at="2026-08-09T11:40:00+00:00",
            ),
        ),
        (3, Headline(title="Undated", url="https://example.test/3")),
    ]

    grouped = rendering.group_headlines_by_age(entries)

    assert [label for label, _items in grouped] == [
        "Last 5 minutes",
        "Last 10 minutes",
        "Last 30 minutes",
        "Older than 1 h",
    ]
    assert [[item[0] for item in items] for _label, items in grouped] == [
        [0],
        [1],
        [2],
        [3],
    ]


def test_relative_age_and_bucket_boundaries_are_stable() -> None:
    """Keep UI labels stable at minute, hour, and day boundaries."""
    assert rendering.resolve_age_bucket(5) == "Last 5 minutes"
    assert rendering.resolve_age_bucket(10) == "Last 10 minutes"
    assert rendering.resolve_age_bucket(30) == "Last 30 minutes"
    assert rendering.resolve_age_bucket(None) == "Older than 1 h"
    assert rendering.format_relative_age(0.5) == "Just now"
    assert rendering.format_relative_age(61) == "1h 1m ago"
    assert rendering.format_relative_age(1_500) == "1d 1h ago"


def test_compose_metadata_parts_uses_section_fallback() -> None:
    """Show section before the generic fallback when detailed metadata is absent."""
    headline = Headline(title="Example", url="https://example.test", section="Markets")

    assert rendering.compose_metadata_parts(headline, None) == ["Markets"]
    assert rendering.compose_metadata_parts(
        Headline(title="Example", url="https://example.test", section=""), None
    ) == ["Unknown source"]
