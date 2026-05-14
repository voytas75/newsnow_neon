"""NewsNow Neon application package bootstrap.

This package houses the modularised components extracted from the legacy
``legacy_app.py`` launcher that previously lived alongside the scripts. All
Tkinter orchestration now resides within this package namespace.

Updates: v0.49.1 - 2025-01-07 - Created package scaffold for modular refactor.
Updates: v0.49.2 - 2025-10-29 - Completed legacy launcher migration into the package.
"""

from __future__ import annotations

from typing import Any


def main(*args: Any, **kwargs: Any) -> None:
    """Import and invoke the real application entrypoint lazily."""
    from .main import main as run_main

    run_main(*args, **kwargs)


__all__ = ["main"]
