"""Fixture-based regression coverage for NewsNow section parsing."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

from newsnow_neon.models import NewsSection


class _FixtureResponse:
    """Minimal successful HTTP response containing fixture markup."""

    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        """Match a successful requests response."""


class _FixtureSession:
    """Capture the request and return fixture markup without network access."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, url: str, **kwargs: object) -> _FixtureResponse:
        """Return a successful fixture response for the requested section URL."""
        self.calls.append((url, kwargs))
        return _FixtureResponse(self._text)


@pytest.fixture()
def section_fixture() -> str:
    """Load representative NewsNow markup from the repository fixture."""
    path = Path(__file__).parent / "fixtures" / "newsnow_section.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture()
def legacy_app_module(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import the parser without loading the Tk-bound application controller."""
    fake_application = types.ModuleType("newsnow_neon.application")
    fake_application.__dict__["AINewsApp"] = type("AINewsApp", (), {})
    fake_application.__dict__["configure_app_services"] = lambda **_kwargs: None
    monkeypatch.setitem(sys.modules, "newsnow_neon.application", fake_application)
    monkeypatch.delitem(sys.modules, "newsnow_neon.legacy_app", raising=False)
    return importlib.import_module("newsnow_neon.legacy_app")


def test_fetch_section_headlines_parses_metadata_and_skips_invalid_entries(
    monkeypatch: pytest.MonkeyPatch,
    section_fixture: str,
    legacy_app_module: types.ModuleType,
) -> None:
    """Parser should preserve metadata and skip duplicate/invalid/cutoff entries."""
    session = _FixtureSession(section_fixture)
    monkeypatch.setattr(legacy_app_module, "get_http_session", lambda: session)
    section = NewsSection("Technology", "https://newsnow.example/technology")

    headlines = legacy_app_module._fetch_section_headlines(section, None, seen=set())

    assert [(headline.title, headline.url) for headline in headlines] == [
        (
            "Alpha headline contains enough words",
            "https://newsnow.example/story/alpha",
        ),
        (
            "Beta headline also has enough words",
            "https://publisher.example/story/beta",
        ),
    ]
    assert headlines[0].source == "Example Wire"
    assert headlines[0].published_time == "just now"
    assert headlines[0].published_at == "1970-01-01T00:00:00Z"
    assert headlines[1].source == "Publisher Example"
    assert headlines[1].published_time == "one minute ago"
    assert headlines[1].published_at == "1970-01-01T00:00:01Z"
    assert session.calls[0][0] == section.url


def test_fetch_section_headlines_honors_item_limit(
    monkeypatch: pytest.MonkeyPatch,
    section_fixture: str,
    legacy_app_module: types.ModuleType,
) -> None:
    """Parser should stop after the requested number of valid headlines."""
    monkeypatch.setattr(
        legacy_app_module,
        "get_http_session",
        lambda: _FixtureSession(section_fixture),
    )
    section = NewsSection("Technology", "https://newsnow.example/technology")

    headlines = legacy_app_module._fetch_section_headlines(section, 1, seen=set())

    assert [headline.title for headline in headlines] == [
        "Alpha headline contains enough words"
    ]


@pytest.mark.parametrize("markup", ["", "<main id='newsfeed'><article>"])
def test_fetch_section_headlines_handles_empty_or_malformed_markup(
    monkeypatch: pytest.MonkeyPatch,
    legacy_app_module: types.ModuleType,
    markup: str,
) -> None:
    """Empty or incomplete markup should produce no headlines instead of raising."""
    monkeypatch.setattr(
        legacy_app_module,
        "get_http_session",
        lambda: _FixtureSession(markup),
    )
    section = NewsSection("Technology", "https://newsnow.example/technology")

    assert legacy_app_module._fetch_section_headlines(section, None, seen=set()) == []
