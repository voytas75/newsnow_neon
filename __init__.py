"""NewsNow Neon application package bootstrap.

This package houses the modularised components extracted from the legacy
``newsnow_neon.py`` script. Over time, the remaining logic in the legacy
module will be migrated into this package.

Updates: v0.49.1 - 2025-01-07 - Created package scaffold for modular refactor.
"""

from .main import main

__all__ = ["main"]
