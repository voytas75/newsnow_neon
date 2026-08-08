"""Regression coverage for headline filtering helpers."""

from __future__ import annotations

from newsnow_neon.app.filtering import filter_headlines, normalise_exclusion_terms
from newsnow_neon.models import Headline


def test_filter_headlines_excludes_terms_from_title_and_source() -> None:
    """Exclude matches case-insensitively while preserving unmatched headlines."""
    headlines = [
        Headline(title="AI launch roadmap", url="https://example.test/ai"),
        Headline(
            title="Market update",
            url="https://example.test/market",
            source="Example Source",
        ),
        Headline(title="Weather update", url="https://example.test/weather"),
    ]

    assert filter_headlines(headlines, {"roadmap", "example source"}) == [headlines[2]]


def test_normalise_exclusion_terms_preserves_order_and_deduplicates() -> None:
    """Keep first normalized terms while ignoring repeated and non-string input."""
    ordered, terms = normalise_exclusion_terms(["AI, ML", " ai ", None, "ML"])

    assert ordered == ["ai", "ml"]
    assert terms == {"ai", "ml"}


def test_normalise_exclusion_terms_ignores_non_text_source() -> None:
    """Treat unsupported persisted exclusion values as no exclusions."""
    assert normalise_exclusion_terms(42) == ([], set())
