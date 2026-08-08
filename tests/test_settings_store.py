"""Regression coverage for persisted settings normalization."""

from __future__ import annotations

import json

import pytest

from newsnow_neon.config import DEFAULT_SETTINGS
from newsnow_neon.settings_store import load_settings


@pytest.mark.parametrize(
    ("stored_value", "expected"),
    [
        ("17", 17),
        ("not-a-number", DEFAULT_SETTINGS["auto_refresh_minutes"]),
        (0, 1),
        (999, 180),
    ],
)
def test_load_settings_normalizes_auto_refresh_minutes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    stored_value: object,
    expected: int,
) -> None:
    """Persisted refresh values must be safe for the Tk integer variable at startup."""
    settings_path = tmp_path / "ainews_settings.json"
    settings_path.write_text(
        json.dumps({"auto_refresh_minutes": stored_value}),
        encoding="utf-8",
    )
    monkeypatch.setattr("newsnow_neon.settings_store.SETTINGS_PATH", settings_path)

    loaded = load_settings()

    assert loaded["auto_refresh_minutes"] == expected


def test_load_settings_invalid_json_returns_defaults(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed persisted JSON should degrade to the documented defaults."""
    settings_path = tmp_path / "ainews_settings.json"
    settings_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr("newsnow_neon.settings_store.SETTINGS_PATH", settings_path)

    loaded = load_settings()

    assert loaded["auto_refresh_minutes"] == DEFAULT_SETTINGS["auto_refresh_minutes"]
    assert loaded["options_visible"] == DEFAULT_SETTINGS["options_visible"]
