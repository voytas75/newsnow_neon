"""Offline regression coverage for summary-resolution fallbacks."""

from __future__ import annotations

import importlib
import sys
import types

import pytest

from newsnow_neon.models import ArticleContent, Headline


@pytest.fixture()
def legacy_app_module(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import summary logic without loading the Tk-bound application controller."""
    fake_application = types.ModuleType("newsnow_neon.application")
    fake_application.__dict__["AINewsApp"] = type("AINewsApp", (), {})
    fake_application.__dict__["configure_app_services"] = lambda **_kwargs: None
    monkeypatch.setitem(sys.modules, "newsnow_neon.application", fake_application)
    monkeypatch.delitem(sys.modules, "newsnow_neon.legacy_app", raising=False)
    return importlib.import_module("newsnow_neon.legacy_app")


@pytest.fixture()
def headline() -> Headline:
    """Return a deterministic headline for summary behavior tests."""
    return Headline(
        title="Important headline requires a safe summary",
        url="https://newsnow.example/article",
    )


def test_resolve_article_summary_uses_original_url_cache_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
    legacy_app_module: types.ModuleType,
    headline: Headline,
) -> None:
    """A primary cache hit must avoid article fetches and provider calls."""
    monkeypatch.setattr(
        legacy_app_module,
        "get_cached_article_summary",
        lambda *_args: "Cached summary",
    )
    monkeypatch.setattr(
        legacy_app_module,
        "_robust_fetch_article_content",
        lambda _url: pytest.fail("article fetch must not run after cache hit"),
    )

    result = legacy_app_module.resolve_article_summary(headline)

    assert result.summary == "Cached summary"
    assert result.article_text is None
    assert result.from_cache is True
    assert result.source_url == headline.url
    assert result.issue is None


def test_resolve_article_summary_falls_back_after_article_fetch_failure(
    monkeypatch: pytest.MonkeyPatch,
    legacy_app_module: types.ModuleType,
    headline: Headline,
) -> None:
    """A failed article fetch should yield a usable headline-only response."""
    monkeypatch.setattr(
        legacy_app_module, "get_cached_article_summary", lambda *_args: None
    )
    monkeypatch.setattr(
        legacy_app_module, "_robust_fetch_article_content", lambda _url: None
    )
    monkeypatch.setattr(
        legacy_app_module,
        "summarize_article",
        lambda *_args, **_kwargs: pytest.fail(
            "provider must not run after fetch failure"
        ),
    )

    result = legacy_app_module.resolve_article_summary(headline)

    assert result.summary.startswith(headline.title)
    assert result.article_text is None
    assert result.from_cache is False
    assert result.source_url is None
    assert result.issue == "article_fetch_failed"


def test_resolve_article_summary_falls_back_when_provider_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    legacy_app_module: types.ModuleType,
    headline: Headline,
) -> None:
    """An invalid empty provider response must not crash the operator workflow."""
    article = ArticleContent(
        url="https://publisher.example/resolved",
        text="First paragraph.\nSecond paragraph.\nThird paragraph.",
    )
    stored: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        legacy_app_module, "get_cached_article_summary", lambda *_args: None
    )
    monkeypatch.setattr(
        legacy_app_module, "_robust_fetch_article_content", lambda _url: article
    )
    monkeypatch.setattr(
        legacy_app_module, "summarize_article", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        legacy_app_module,
        "store_cached_article_summary",
        lambda *args: stored.append(args),
    )

    result = legacy_app_module.resolve_article_summary(headline)

    assert result.summary == "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    assert result.article_text == article.text
    assert result.from_cache is False
    assert result.source_url == article.url
    assert result.issue == "summary_generation_empty"
    assert stored == []


def test_resolve_article_summary_falls_back_when_provider_raises(
    monkeypatch: pytest.MonkeyPatch,
    legacy_app_module: types.ModuleType,
    headline: Headline,
) -> None:
    """An unexpected provider exception must not escape to the operator UI."""
    article = ArticleContent(
        url="https://publisher.example/resolved",
        text="Article excerpt for a failed provider call.",
    )
    monkeypatch.setattr(
        legacy_app_module, "get_cached_article_summary", lambda *_args: None
    )
    monkeypatch.setattr(
        legacy_app_module, "_robust_fetch_article_content", lambda _url: article
    )

    def _raise_provider(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(legacy_app_module, "summarize_article", _raise_provider)

    result = legacy_app_module.resolve_article_summary(headline)

    assert result.summary == article.text
    assert result.article_text == article.text
    assert result.from_cache is False
    assert result.source_url == article.url
    assert result.issue == "summary_generation_failed"
