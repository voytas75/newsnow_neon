"""Offline regression tests for legacy helper consolidation."""

from __future__ import annotations

import ast
import importlib
import sys
import types
from collections import Counter
from pathlib import Path

import pytest

_HELPER_NAMES = {
    "_normalize_href",
    "_resolve_final_url",
    "_extract_completion_text",
}


@pytest.fixture()
def legacy_app_module(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import the legacy helpers without loading the Tk-bound app controller."""
    fake_application = types.ModuleType("newsnow_neon.application")
    fake_application.__dict__["AINewsApp"] = type("AINewsApp", (), {})
    fake_application.__dict__["configure_app_services"] = lambda **_kwargs: None
    monkeypatch.setitem(sys.modules, "newsnow_neon.application", fake_application)
    monkeypatch.delitem(sys.modules, "newsnow_neon.legacy_app", raising=False)
    return importlib.import_module("newsnow_neon.legacy_app")


def test_legacy_helper_names_have_one_top_level_definition() -> None:
    """Keep helper declarations singular so later copies cannot shadow behavior."""
    legacy_path = Path(__file__).parents[1] / "newsnow_neon" / "legacy_app.py"
    tree = ast.parse(legacy_path.read_text(encoding="utf-8"))
    counts = Counter(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in _HELPER_NAMES
    )

    assert counts == {name: 1 for name in _HELPER_NAMES}


def test_retained_legacy_helpers_keep_offline_contract(
    legacy_app_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve the active helper behavior while redundant copies are removed."""
    assert legacy_app_module._normalize_href(None) is None
    assert legacy_app_module._normalize_href([]) is None
    assert legacy_app_module._normalize_href(["/article"]) == "/article"
    assert legacy_app_module._normalize_href(42) == "42"

    redirect_response = types.SimpleNamespace(
        history=[object()],
        url="https://publisher.example/article",
        status_code=200,
        headers={},
    )
    session = types.SimpleNamespace(head=lambda *_args, **_kwargs: redirect_response)
    monkeypatch.setattr(legacy_app_module, "get_http_session", lambda: session)
    assert (
        legacy_app_module._resolve_final_url("https://newsnow.example/redirect")
        == "https://publisher.example/article"
    )

    completion = {
        "choices": [{"message": {"content": [{"text": " first "}, "second"]}}]
    }
    assert legacy_app_module._extract_completion_text(completion) == "first second"
