"""Compatibility wrapper for the app.controller package surface.

Updates: v0.52 - 2025-11-18 - Introduced modular controller wrapper that
re-exported the legacy AINewsApp to preserve behavior while enabling a
package-based structure (app.controller).
Updates: v0.53.4 - 2026-05-14 - Narrowed this file to a truthful compatibility
alias so it matches the package export instead of creating a second subclass
surface.
"""

from __future__ import annotations

from ..application import AINewsApp

__all__ = ["AINewsApp"]
