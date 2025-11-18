from __future__ import annotations

import logging
import threading
from typing import Any, List, Optional, Set, Tuple
from urllib.parse import urlparse

import tkinter as tk
from tkinter import messagebox

from ..actions import (
    derive_source_term as _derive_source_term_fn,
    extract_keyword_for_mute as _extract_keyword_for_mute_fn,
)
from ..filtering import (
    normalise_exclusion_terms as _normalise_exclusion_terms_fn,
    split_exclusion_string as _split_exclusion_string_fn,
)

logger = logging.getLogger(__name__)


class ExclusionsController:
    """Handle exclusion terms, mute actions, and related UI state.

    This controller centralizes:
    - parsing/normalizing exclusion terms
    - applying/clearing exclusions and persisting settings
    - enabling/disabling 'Mute' action buttons based on selection
    - one-click mute for keyword/source with background resolution
    """

    def __init__(self, app: "AINewsApp") -> None:
        self.app = app

    # Public API used by AINewsApp -------------------------------------------------

    def normalise_exclusion_terms(self, source: Any) -> Tuple[List[str], Set[str]]:
        """Normalize exclusion terms using shared filtering helpers."""
        # Delegate to app.filtering implementation for consistency.
        # It supports both strings and sequences of strings.
        try:
            terms_list, terms_set = _normalise_exclusion_terms_fn(source)
        except TypeError:
            # Fall back to manual path mirroring previous behavior.
            candidates: List[str] = []
            if isinstance(source, str):
                candidates.extend(_split_exclusion_string_fn(source))
            elif isinstance(source, (list, tuple, set)):
                for item in source:
                    if isinstance(item, str):
                        candidates.extend(_split_exclusion_string_fn(item))
            unique_terms: List[str] = []
            seen: Set[str] = set()
            for candidate in candidates:
                cleaned = candidate.strip()
                if not cleaned:
                    continue
                lowered = cleaned.lower()
                if lowered in seen:
                    continue
                unique_terms.append(cleaned)
                seen.add(lowered)
            terms_list, terms_set = unique_terms, seen
        return terms_list, terms_set

    def apply_exclusion_terms(
        self, event: Optional[tk.Event] = None
    ) -> Optional[str]:
        """Apply exclusions from the text var, persist, and re-render."""
        value = self.app.exclude_terms_var.get()
        terms_list, terms_set = self.normalise_exclusion_terms(value)
        self.app.exclude_terms_var.set(", ".join(terms_list))

        if terms_set == getattr(self.app, "_exclusion_terms", set()) and terms_list == (
            self.app.settings.get("headline_exclusions", [])
        ):
            if event is not None and getattr(event, "keysym", None) == "Return":
                return "break"
            return None

        self.app._exclusion_terms = terms_set
        self.app.settings["headline_exclusions"] = terms_list
        self.app._save_settings()
        self.app._reapply_exclusion_filters(log_status=True)
        if event is not None and getattr(event, "keysym", None) == "Return":
            return "break"
        return None

    def clear_exclusion_terms(self) -> None:
        """Clear exclusions if any and re-apply filtering."""
        if not getattr(self.app, "_exclusion_terms", set()) and not (
            self.app.exclude_terms_var.get().strip()
        ):
            return
        self.app.exclude_terms_var.set("")
        self.apply_exclusion_terms()

    def refresh_mute_button_state(self) -> None:
        """Enable/disable mute buttons based on current selection."""
        app = self.app
        if not hasattr(app, "mute_source_btn") or not hasattr(app, "mute_keyword_btn"):
            return

        headline = self._resolve_selected_headline()
        enable_source = False
        enable_keyword = False
        if headline is not None:
            url_val = headline.url if isinstance(headline.url, str) else ""
            src_val = headline.source if isinstance(headline.source, str) else ""
            enable_source = bool(url_val.strip() or src_val.strip())
            title_val = headline.title if isinstance(headline.title, str) else ""
            enable_keyword = bool(_extract_keyword_for_mute_fn(title_val))

        try:
            app.mute_source_btn.config(state=(tk.NORMAL if enable_source else tk.DISABLED))
            app.mute_keyword_btn.config(state=(tk.NORMAL if enable_keyword else tk.DISABLED))
        except Exception:
            logger.debug("Unable to update mute action button state.")

    def add_exclusion_term(self, term: str, *, show_feedback: bool = True) -> bool:
        """Append a term asynchronously; persist and re-render on completion."""
        app = self.app
        cleaned = (term or "").strip()
        if not cleaned:
            return False

        # Disable actions and show short status to keep UI responsive.
        try:
            if hasattr(app, "mute_source_btn"):
                app.mute_source_btn.config(state=tk.DISABLED)
            if hasattr(app, "mute_keyword_btn"):
                app.mute_keyword_btn.config(state=tk.DISABLED)
        except Exception:
            pass
        app._log_status("Applying exclusion…")

        current_text = app.exclude_terms_var.get() if hasattr(app, "exclude_terms_var") else ""

        def worker() -> None:
            combined = f"{current_text}, {cleaned}" if current_text.strip() else cleaned
            terms_list, terms_set = self.normalise_exclusion_terms(combined)
            is_changed = terms_set != getattr(app, "_exclusion_terms", set())

            def finalize() -> None:
                if not is_changed:
                    if show_feedback:
                        app._log_status(f"Exclusion term already present: '{cleaned}'.")
                    self.refresh_mute_button_state()
                    return
                app._exclusion_terms = terms_set
                app.settings["headline_exclusions"] = terms_list
                if hasattr(app, "exclude_terms_var"):
                    app.exclude_terms_var.set(", ".join(terms_list))
                app._save_settings()
                app._reapply_exclusion_filters(log_status=True)
                self.refresh_mute_button_state()
                if show_feedback:
                    app._log_status(f"Added exclusion term: '{cleaned}'.")

            app.after(0, finalize)

        threading.Thread(target=worker, daemon=True).start()
        return True

    def mute_selected_source(self) -> None:
        """Mute the source (final article domain or derived label) of the selection."""
        app = self.app
        headline = self._resolve_selected_headline()
        if headline is None:
            return

        def worker() -> None:
            term: Optional[str] = None
            url_val = headline.url if isinstance(headline.url, str) else ""
            if url_val.strip():
                try:
                    # Lightweight final-URL resolution via shared HTTP client
                    from ...http_client import resolve_final_url

                    resolved = resolve_final_url(url_val, timeout=8)
                    parsed = urlparse(resolved)
                    netloc = parsed.netloc or ""
                    # Normalize domain: strip auth/port and www prefix
                    netloc = netloc.split("@")[-1].split(":")[0].lower()
                    if netloc.startswith("www."):
                        netloc = netloc[4:]
                    # Avoid muting NewsNow redirector domains
                    redirect_suffixes = ("newsnow.com", "newsnow.co.uk")
                    if netloc and not any(netloc.endswith(s) for s in redirect_suffixes):
                        term = netloc
                except Exception:
                    term = None

            if not term:
                try:
                    term = _derive_source_term_fn(headline)
                except Exception:
                    term = None

            def finalize() -> None:
                if not term:
                    messagebox.showinfo(
                        "Mute Source",
                        "Unable to derive a source to mute for this item.",
                    )
                    return
                self.add_exclusion_term(term, show_feedback=True)

            app.after(0, finalize)

        threading.Thread(target=worker, daemon=True).start()

    def mute_selected_keyword(self) -> None:
        """Mute a heuristic keyword derived from the selected headline's title."""
        app = self.app
        headline = self._resolve_selected_headline()
        if headline is None:
            return
        title_val = headline.title if isinstance(headline.title, str) else ""
        keyword = _extract_keyword_for_mute_fn(title_val)
        if not keyword:
            messagebox.showinfo(
                "Mute Keyword", "Unable to derive a keyword to mute from the title."
            )
            return
        self.add_exclusion_term(keyword, show_feedback=True)

    # Internal helpers -------------------------------------------------------------

    def _resolve_selected_headline(self):
        """Resolve current selection via the application accessor."""
        # Use the app's existing resolution to avoid duplicating selection logic.
        try:
            return self.app._resolve_selected_headline()
        except Exception:  # pragma: no cover - defensive guard
            return None
