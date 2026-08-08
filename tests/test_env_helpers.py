"""Regression coverage for safe environment-value logging."""

from __future__ import annotations

from newsnow_neon.app.helpers.env_helpers import sanitize_env_value


def test_sanitize_env_value_masks_sensitive_nonempty_value() -> None:
    """Prevent API-like values from reaching diagnostic output."""
    assert sanitize_env_value("OPENAI_API_KEY", "super-secret") == "***"
    assert sanitize_env_value("SESSION_TOKEN", "session-secret") == "***"


def test_sanitize_env_value_preserves_safe_values_and_truncates_long_values() -> None:
    """Keep ordinary values readable while bounding verbose diagnostics."""
    assert sanitize_env_value("APP_MODE", "development") == "development"
    assert sanitize_env_value("APP_MODE", "a" * 81) == "a" * 77 + "…"


def test_sanitize_env_value_omits_empty_values() -> None:
    """Do not emit absent or blank-sensitive values into diagnostics."""
    assert sanitize_env_value("APP_MODE", None) is None
    assert sanitize_env_value("OPENAI_API_KEY", "") is None
