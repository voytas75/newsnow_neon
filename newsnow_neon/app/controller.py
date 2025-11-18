"""Tkinter application controller integration (modular package wrapper).

Updates: v0.52 - 2025-11-18 - Introduced modular controller wrapper that
re-exports the legacy AINewsApp to preserve behavior while enabling a
package-based structure (app.controller).
"""

from __future__ import annotations

from ..application import AINewsApp as _LegacyAINewsApp


class AINewsApp(_LegacyAINewsApp):
    """Modular controller class inheriting the legacy implementation.

    This wrapper maintains the existing UI behavior while allowing new
    code to import the controller from 'newsnow_neon.app.controller'
    instead of the monolithic 'newsnow_neon.application' module.
    """
    pass


__all__ = ["AINewsApp"]