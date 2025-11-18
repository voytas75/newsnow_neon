"""SettingsController centralizes settings, profiles, timezone, and geometry.

Updates: v0.52 - 2025-11-18 - Introduce controller scaffold delegating to
current AINewsApp methods to preserve behavior while refactoring; future
iterations will migrate logic fully here (apply/reset, color profiles,
timezone handling, window geometry persistence, and options visibility).
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

import tkinter as tk

if TYPE_CHECKING:
    # Forward-declare to avoid circular import at runtime.
    from ...application import AINewsApp


logger = logging.getLogger(__name__)


class SettingsController:
    """Encapsulates settings workflow, appearance, and timing toggles.

    This scaffold wires UI commands to app methods and keeps state changes
    unified. Subsequent refactors can move the core logic inside these
    methods to minimize monolith responsibilities in AINewsApp.
    """

    def __init__(self, app: "AINewsApp") -> None:
        """Bind to the Tk application orchestrator instance."""
        self.app = app

    # Public API — toggles and updates

    def toggle_debug_mode(self) -> None:
        """Toggle debug logging mode."""
        self.app._toggle_debug_mode()

    def toggle_litellm_debug(self) -> None:
        """Toggle LiteLLM debugging."""
        self.app._toggle_litellm_debug()

    def toggle_historical_cache(self) -> None:
        """Toggle 24h history caching."""
        self.app._toggle_historical_cache()

    def toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh behavior and reschedule."""
        self.app._toggle_auto_refresh()

    def toggle_background_watch(self) -> None:
        """Toggle background watch and schedule accordingly."""
        self.app._toggle_background_watch()

    def update_auto_refresh_minutes(self, *_args: object) -> None:
        """Apply auto-refresh minutes and reschedule."""
        self.app._update_auto_refresh_minutes()

    # Appearance — color profiles and colors

    def apply_color_profile(self, selected: Optional[str] = None) -> None:
        """Apply the selected color profile to tickers and save setting."""
        self.app._apply_color_profile(selected)

    def on_profile_selected(self, name: str) -> None:
        """Handle color profile option selection."""
        self.app._on_profile_selected(name)

    def refresh_color_profiles(self) -> None:
        """Expose profile menu refresh for dynamic profile additions."""
        self.app.refresh_color_profiles()

    def choose_color(self, target: str) -> None:
        """Open color chooser for background/text and apply."""
        self.app._choose_color(target)

    def update_ticker_colors(self) -> None:
        """Update ticker colors with current vars and persist."""
        self.app._update_ticker_colors()

    def refresh_profile_menu(self) -> None:
        """Rebuild the color profile option menu."""
        self.app._refresh_profile_menu()

    # Timezone

    def on_timezone_change(self, *_args: object) -> None:
        """Handle timezone option change via traced StringVar."""
        self.app._on_timezone_change()

    def apply_timezone_selection(self, value: str, *, persist: bool) -> None:
        """Apply selected timezone, update menus, and re-render labels."""
        self.app._apply_timezone_selection(value, persist=persist)

    def refresh_timezone_menu(self) -> None:
        """Rebuild the timezone option menu."""
        self.app._refresh_timezone_menu()

    def refresh_timezone_display(self) -> None:
        """Re-render headlines/ticker with current timezone."""
        self.app._refresh_timezone_display()

    # Options visibility

    def toggle_options_panel(self) -> None:
        """Toggle options panel visibility."""
        self.app._toggle_options_panel()

    def set_options_visibility(self, visible: bool, *, persist: bool = True) -> None:
        """Set options visibility and optionally persist to settings."""
        self.app._set_options_visibility(visible, persist=persist)

    # Geometry and root configure

    def on_root_configure(self, event: tk.Event) -> None:
        """Handle root Configure events to persist window geometry."""
        self.app._on_root_configure(event)

    def remember_window_geometry(self) -> None:
        """Persist current or last-known window geometry to settings."""
        self.app._remember_window_geometry()

    # Settings lifecycle

    def apply_settings_from_store(self) -> None:
        """Apply settings from persistent store to the UI state."""
        self.app._apply_settings_from_store()

    def save_settings(self) -> None:
        """Persist current settings to the store."""
        self.app._save_settings()

    def reset_settings(self) -> None:
        """Reset settings to defaults and reapply UI state."""
        self.app._reset_settings()

    # Status/Logging summary

    def update_status_summary(self) -> None:
        """Update condensed status summary when options are hidden."""
        self.app._update_status_summary()

    def update_handler_level(self) -> None:
        """Update logging handler levels according to debug setting."""
        self.app._update_handler_level()


__all__ = ["SettingsController"]