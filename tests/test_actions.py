"""Regression coverage for headline mute-term helpers."""

from __future__ import annotations

from newsnow_neon.app import actions
from newsnow_neon.models import Headline


def test_extract_keyword_for_mute_skips_stopwords_and_numbers() -> None:
    """Return the first useful token after generic words and numbers."""
    assert actions.extract_keyword_for_mute("New 2026 AI regulation") == "regulation"


def test_extract_keyword_for_mute_returns_none_without_useful_token() -> None:
    """Return no mute keyword when the title has no useful token."""
    assert actions.extract_keyword_for_mute("the and 2026") is None


def test_derive_source_term_prefers_resolved_article_domain(monkeypatch) -> None:
    """Prefer the final article domain over the NewsNow redirector."""
    monkeypatch.setattr(
        "newsnow_neon.http_client.resolve_final_url",
        lambda _url, timeout: "https://www.example.org/article",
    )

    headline = Headline(
        title="Example headline",
        url="https://newsnow.co.uk/story",
        source="Example source",
    )

    assert actions.derive_source_term(headline) == "example.org"


def test_derive_source_term_falls_back_to_source_for_newsnow_redirect() -> None:
    """Use the source label when the URL remains a NewsNow redirector."""
    headline = Headline(
        title="Example headline",
        url="https://newsnow.co.uk/story",
        source="Example source",
    )

    assert actions.derive_source_term(headline) == "Example source"
