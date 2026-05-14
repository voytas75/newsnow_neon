"""Tests for browser launch behavior in Linux/root/headless scenarios."""

from __future__ import annotations

import logging
import subprocess
import webbrowser

import pytest

from newsnow_neon import browser_launcher


def test_open_url_uses_webbrowser_for_normal_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-root sessions should use the standard webbrowser launcher."""
    opened: list[str] = []

    monkeypatch.setattr(browser_launcher, "is_linux_root_session", lambda: False)
    monkeypatch.setattr(
        browser_launcher.webbrowser,
        "open_new_tab",
        lambda url: opened.append(url) or True,
    )

    assert browser_launcher.open_url("https://example.com/article") is True
    assert opened == ["https://example.com/article"]


def test_open_url_linux_root_uses_xdg_open_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Linux root sessions should prefer xdg-open over Chromium webbrowser helpers."""
    calls: list[list[str]] = []

    monkeypatch.setattr(browser_launcher, "is_linux_root_session", lambda: True)
    monkeypatch.setattr(
        browser_launcher.shutil,
        "which",
        lambda _name: "/usr/bin/xdg-open",
    )

    def fake_run(
        argv: list[str],
        *,
        check: bool,
        stdout: int,
        stderr: int,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert check is False
        assert stdout is subprocess.DEVNULL
        assert stderr is subprocess.DEVNULL
        assert timeout == 10
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(browser_launcher.subprocess, "run", fake_run)

    assert browser_launcher.open_url("https://example.com/article") is True
    assert calls == [["/usr/bin/xdg-open", "https://example.com/article"]]


def test_open_url_linux_root_logs_warning_when_no_safe_launcher(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Linux root sessions should avoid Chromium launch and log guidance instead."""
    monkeypatch.setattr(browser_launcher, "is_linux_root_session", lambda: True)
    monkeypatch.setattr(browser_launcher.shutil, "which", lambda _name: None)

    def fail_open(_url: str) -> bool:
        raise AssertionError("webbrowser should not be called for Linux root fallback")

    monkeypatch.setattr(browser_launcher.webbrowser, "open_new_tab", fail_open)

    with caplog.at_level(logging.WARNING):
        assert browser_launcher.open_url("https://example.com/article") is False

    assert browser_launcher.ROOT_LINUX_BROWSER_ERROR_MESSAGE in caplog.text


def test_open_url_returns_false_when_webbrowser_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Standard browser launch errors should be downgraded to a False result."""
    monkeypatch.setattr(browser_launcher, "is_linux_root_session", lambda: False)

    def fail_open(_url: str) -> bool:
        raise webbrowser.Error("boom")

    monkeypatch.setattr(browser_launcher.webbrowser, "open_new_tab", fail_open)

    assert browser_launcher.open_url("https://example.com/article") is False