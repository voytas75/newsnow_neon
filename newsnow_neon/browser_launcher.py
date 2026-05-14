"""Safe URL launching helpers for desktop/browser integration.

Updates: v0.53.1 - 2026-05-14 - Added Linux/root-aware browser launcher to
avoid noisy sandbox errors when opening article links.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import webbrowser

logger = logging.getLogger(__name__)

ROOT_LINUX_BROWSER_ERROR_MESSAGE = (
    "Cannot open the article link from this Linux session because the app is "
    "running as root and Chromium-based browsers require --no-sandbox in that "
    "mode. Open the link from a normal desktop user session or configure a "
    "non-Chromium browser as the default browser."
)


def is_linux_root_session() -> bool:
    """Return whether the process runs as root on Linux."""
    geteuid = getattr(os, "geteuid", None)
    return platform.system() == "Linux" and callable(geteuid) and geteuid() == 0


def open_url(url: str) -> bool:
    """Open a URL and absorb Linux root/Chromium launch failures.

    Returns True when a browser launch was dispatched, otherwise False.
    """
    if is_linux_root_session():
        return _open_url_linux_root(url)

    try:
        return bool(webbrowser.open_new_tab(url))
    except webbrowser.Error:
        logger.exception("Browser launch failed for URL: %s", url)
        return False


def _open_url_linux_root(url: str) -> bool:
    """Open a URL under Linux root using conservative fallbacks."""
    if _try_xdg_open(url):
        return True

    logger.warning(ROOT_LINUX_BROWSER_ERROR_MESSAGE)
    return False


def _try_xdg_open(url: str) -> bool:
    """Try xdg-open only when available; ignore failures quietly."""
    xdg_open = shutil.which("xdg-open")
    if not xdg_open:
        return False

    try:
        completed = subprocess.run(
            [xdg_open, url],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        logger.exception("xdg-open failed for URL: %s", url)
        return False

    return completed.returncode == 0


__all__ = ["ROOT_LINUX_BROWSER_ERROR_MESSAGE", "is_linux_root_session", "open_url"]