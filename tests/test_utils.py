"""Unit tests for utility functions in newsnow_neon.utils.

Covers:
- read_optional_env
- compute_deadline_timeout
- isoformat_epoch
- parse_iso8601_utc
"""

from __future__ import annotations

import time
from datetime import timezone

import pytest

from newsnow_neon.utils import (
    read_optional_env,
    compute_deadline_timeout,
    isoformat_epoch,
    parse_iso8601_utc,
)


def test_read_optional_env_returns_trimmed_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment value should be trimmed and returned when non-blank."""
    monkeypatch.setenv("TEST_ENV_VAR", "  value  ")
    assert read_optional_env("TEST_ENV_VAR") == "value"


def test_read_optional_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset environment variable should yield None."""
    monkeypatch.delenv("MISSING_ENV_VAR", raising=False)
    assert read_optional_env("MISSING_ENV_VAR") is None


def test_read_optional_env_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blank environment variable should yield None."""
    monkeypatch.setenv("BLANK_ENV_VAR", "   ")
    assert read_optional_env("BLANK_ENV_VAR") is None


def test_compute_deadline_timeout_none_deadline() -> None:
    """When deadline is None, fallback should be used as timeout."""
    assert compute_deadline_timeout(None, fallback=5.0) == 5.0


def test_compute_deadline_timeout_positive_remaining() -> None:
    """When deadline is in the future, timeout should be bounded by remaining."""
    deadline = time.monotonic() + 2.5
    timeout = compute_deadline_timeout(deadline, fallback=10.0)
    # Should be clamped to remaining time, and at least 1.0
    assert timeout is not None
    assert 1.0 <= timeout <= 2.5


def test_compute_deadline_timeout_past_deadline() -> None:
    """When deadline has passed, timeout should be None."""
    deadline = time.monotonic() - 0.5
    assert compute_deadline_timeout(deadline, fallback=5.0) is None


def test_isoformat_epoch_valid_zero() -> None:
    """Epoch '0' should render to canonical UTC Z form."""
    assert isoformat_epoch("0") == "1970-01-01T00:00:00Z"


def test_isoformat_epoch_one_second() -> None:
    """Epoch '1' should render a one-second offset in UTC."""
    assert isoformat_epoch("1") == "1970-01-01T00:00:01Z"


def test_isoformat_epoch_invalid_returns_none() -> None:
    """Non-integer text should yield None."""
    assert isoformat_epoch("not-an-int") is None


def test_isoformat_epoch_blank_returns_none() -> None:
    """Blank or whitespace-only text should yield None."""
    assert isoformat_epoch("   ") is None


def test_parse_iso8601_utc_z_suffixed() -> None:
    """Z-suffixed ISO-8601 strings should parse as UTC-aware datetimes."""
    dt = parse_iso8601_utc("1970-01-01T00:00:00Z")
    assert dt is not None
    assert dt.tzinfo == timezone.utc


def test_parse_iso8601_utc_none_returns_none() -> None:
    """None input should yield None."""
    assert parse_iso8601_utc(None) is None


def test_parse_iso8601_utc_invalid_returns_none() -> None:
    """Invalid ISO-8601 text should yield None."""
    assert parse_iso8601_utc("definitely-not-iso8601") is None


def test_parse_iso8601_utc_naive_becomes_aware_utc() -> None:
    """Naive timestamps should be normalized to UTC-aware datetimes."""
    dt = parse_iso8601_utc("2025-01-01T12:00:00")
    assert dt is not None
    assert dt.tzinfo == timezone.utc