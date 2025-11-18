"""App info window extracted from ui.py.

Updates: v0.52 - 2025-11-18 - Extracted AppInfoWindow into ui/windows.
"""
from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable, Optional, Sequence, Tuple
import webbrowser

from ...models import AppMetadata

logger = logging.getLogger(__name__)


class AppInfoWindow(tk.Toplevel):
    """Display application metadata and a system snapshot."""

    def __init__(
        self,
        master: tk.Misc,
        metadata: AppMetadata,
        system_rows: Sequence[Tuple[str, str]],
        on_close: Optional[Callable[[], None]],
    ) -> None:
        super().__init__(master)
        self._on_close = on_close
        self._on_close_invoked = False

        self.title(f"About {metadata.name}")
        self.configure(bg="black")
        self.resizable(False, False)
        self.transient(master)
        self.geometry("480x420")
        self.protocol("WM_DELETE_WINDOW", self._handle_close)
        self.bind("<Escape>", lambda _event: self._handle_close())

        title_label = tk.Label(
            self,
            text=metadata.name,
            font=("Segoe UI", 16, "bold"),
            bg="black",
            fg="white",
        )
        title_label.pack(pady=(18, 4))

        version_label = tk.Label(
            self,
            text=f"Version {metadata.version}",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10),
        )
        version_label.pack()

        description_label = tk.Label(
            self,
            text=metadata.description,
            bg="black",
            fg="lightgray",
            wraplength=420,
            justify="left",
            font=("Segoe UI", 10),
        )
        description_label.pack(padx=20, pady=(6, 14))

        info_frame = tk.Frame(self, bg="black")
        info_frame.pack(fill="x", padx=20)

        for label_text, value_text in system_rows:
            self._add_kv_row(info_frame, label_text, value_text)

        author_value = metadata.author
        author_link = (
            author_value
            if isinstance(author_value, str)
            and author_value.startswith(("http://", "https://"))
            else None
        )
        self._add_kv_row(info_frame, "Author", author_value, link_url=author_link)

        if metadata.donate_url:
            self._add_kv_row(
                info_frame, "Support", metadata.donate_url, link_url=metadata.donate_url
            )
        else:
            self._add_kv_row(
                info_frame,
                "Support",
                "Set NEWSNOW_DONATE_URL to share a donation link.",
            )

        button_frame = tk.Frame(self, bg="black")
        button_frame.pack(fill="x", padx=20, pady=(16, 18))
        close_button = tk.Button(button_frame, text="Close", command=self._handle_close)
        close_button.pack(side="right")
        close_button.focus_set()

    def _add_kv_row(
        self,
        container: tk.Misc,
        key: str,
        value: str,
        *,
        link_url: Optional[str] = None,
    ) -> None:
        row = tk.Frame(container, bg="black")
        row.pack(fill="x", pady=2)
        key_label = tk.Label(
            row,
            text=f"{key}:",
            bg="black",
            fg="lightgray",
            font=("Segoe UI", 10, "bold"),
            width=18,
            anchor="w",
        )
        key_label.pack(side="left")
        if link_url:
            link_color = "#4DA6FF"
            value_label = tk.Label(
                row,
                text=value,
                bg="black",
                fg=link_color,
                cursor="hand2",
                wraplength=320,
                justify="left",
                anchor="w",
            )
            value_label.pack(fill="x", padx=(8, 0))
            value_label.bind(
                "<Button-1>", lambda _event, url=link_url: webbrowser.open_new_tab(url)
            )
            value_label.bind(
                "<Enter>", lambda _event, widget=value_label: widget.config(fg="#80C4FF")
            )
            value_label.bind(
                "<Leave>", lambda _event, widget=value_label: widget.config(fg=link_color)
            )
        else:
            value_label = tk.Label(
                row,
                text=value,
                bg="black",
                fg="white",
                wraplength=320,
                justify="left",
                anchor="w",
            )
            value_label.pack(fill="x", padx=(8, 0))

    def _handle_close(self) -> None:
        if self._on_close_invoked:
            return
        self._on_close_invoked = True
        if self._on_close:
            try:
                self._on_close()
            except Exception:  # pragma: no cover - safeguard
                logger.exception("Error running app info close callback.")
        self.destroy()


__all__ = ["AppInfoWindow"]