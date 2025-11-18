"""Domain and UI models backing the NewsNow Neon application.

This module collects the primary dataclasses and lightweight Tk widgets that
were previously embedded in the legacy launcher (now ``legacy_app.py``).
Moving the definitions here allows other layers (networking, orchestration, UI
composition) to import them without triggering the entire application.

Updates: v0.49.1 - 2025-01-07 - Extracted core model and widget classes.
Updates: v0.49.2 - 2025-10-29 - Documented packaged launcher rename.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, FrozenSet, List, Literal, Mapping, Optional

import tkinter as tk


@dataclass(frozen=True)
class AppMetadata:
    name: str
    version: str
    author: str
    donate_url: Optional[str]
    description: str


@dataclass(frozen=True)
class NewsSection:
    label: str
    url: str


@dataclass(frozen=True)
class Headline:
    title: str
    url: str
    section: str = "News"
    source: Optional[str] = None
    published_time: Optional[str] = None
    published_at: Optional[str] = None

    def as_dict(self) -> Dict[str, str]:
        payload: Dict[str, str] = {"title": self.title, "url": self.url, "section": self.section}
        if self.source:
            payload["source"] = self.source
        if self.published_time:
            payload["published_time"] = self.published_time
        if self.published_at:
            payload["published_at"] = self.published_at
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> Optional["Headline"]:
        title = payload.get("title")
        url = payload.get("url")
        if not isinstance(title, str) or not isinstance(url, str):
            return None
        section = payload.get("section") if isinstance(payload.get("section"), str) else "News"
        source = payload.get("source") if isinstance(payload.get("source"), str) else None
        published_time = (
            payload.get("published_time") if isinstance(payload.get("published_time"), str) else None
        )
        published_at = (
            payload.get("published_at") if isinstance(payload.get("published_at"), str) else None
        )
        return cls(
            title=title,
            url=url,
            section=section,
            source=source,
            published_time=published_time,
            published_at=published_at,
        )


@dataclass(frozen=True)
class HeadlineCache:
    headlines: List[Headline]
    ticker_text: Optional[str] = None
    summaries: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Any) -> Optional["HeadlineCache"]:
        if isinstance(payload, dict):
            headlines_data = payload.get("headlines", [])
            ticker_text = payload.get("ticker")
            summaries_data = payload.get("summaries", {})
        else:
            headlines_data = payload
            ticker_text = None
            summaries_data = {}

        if not isinstance(headlines_data, list):
            return None

        headlines: List[Headline] = []
        for entry in headlines_data:
            if not isinstance(entry, dict):
                continue
            headline = Headline.from_dict(entry)
            if headline is not None:
                headlines.append(headline)

        if isinstance(ticker_text, str) and ticker_text.strip():
            normalized_ticker: Optional[str] = ticker_text
        else:
            normalized_ticker = None

        summaries: Dict[str, str] = {}
        if isinstance(summaries_data, Mapping):
            for key, value in summaries_data.items():
                if isinstance(key, str) and isinstance(value, str) and value.strip():
                    summaries[key] = value

        return cls(headlines=headlines, ticker_text=normalized_ticker, summaries=summaries)

    def limited(self, max_items: Optional[int]) -> "HeadlineCache":
        if max_items is None or max_items >= len(self.headlines):
            return self
        limited_headlines = list(self.headlines[: max_items])
        return HeadlineCache(
            headlines=limited_headlines,
            ticker_text=self.ticker_text,
            summaries=self.summaries,
        )

    def to_payload(self) -> Dict[str, Any]:
        return {
            "headlines": [item.as_dict() for item in self.headlines],
            "ticker": self.ticker_text,
            "summaries": dict(self.summaries),
        }


@dataclass(frozen=True)
class RedisStatistics:
    cache_configured: bool
    available: bool
    cache_key: str
    key_present: bool
    headline_count: int = 0
    summary_count: int = 0
    ticker_present: bool = False
    sections: List[str] = field(default_factory=list)
    section_count: int = 0
    sources: List[str] = field(default_factory=list)
    source_count: int = 0
    ttl_seconds: Optional[int] = None
    payload_bytes: Optional[int] = None
    latest_headline_time: Optional[datetime] = None
    latest_headline_title: Optional[str] = None
    latest_headline_source: Optional[str] = None
    historical_snapshot_count: int = 0
    latest_snapshot_key: Optional[str] = None
    dbsize: Optional[int] = None
    redis_version: Optional[str] = None
    connected_clients: Optional[int] = None
    used_memory_human: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass(frozen=True)
class HistoricalSnapshot:
    key: str
    captured_at: datetime
    cache: HeadlineCache
    headline_count: int
    summary_count: int


@dataclass(frozen=True)
class ArticleContent:
    url: str
    text: str


@dataclass(frozen=True)
class SummaryResolution:
    summary: str
    article_text: Optional[str]
    from_cache: bool
    source_url: Optional[str] = None
    issue: Optional[str] = None


@dataclass(frozen=True)
class HeadlineTooltipData:
    headline: Headline
    relative_age: Optional[str] = None
    display_index: Optional[int] = None
    row_kind: Literal["title", "metadata"] = "title"


@dataclass(frozen=True)
class LiveFlowState:
    next_refresh_time: Optional[datetime]
    auto_refresh_enabled: bool
    background_watch_enabled: bool
    background_watch_next_run: Optional[datetime]
    pending_new_headlines: int
    last_reported_pending: int
    background_candidate_keys: FrozenSet[tuple[str, str]]
    listbox_view_top: Optional[float]
    listbox_selection: Optional[int]


class HoverTooltip:
    """Reusable tooltip window for hover interactions."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        background: str = "#1e1e1e",
        foreground: str = "white",
        wraplength: int = 440,
    ) -> None:
        self.master = master
        self.background = background
        self.foreground = foreground
        self.wraplength = wraplength
        self._window: Optional[tk.Toplevel] = None
        self._label: Optional[tk.Label] = None
        self._visible = False
        self._current_text: str = ""
        try:
            self.master.bind("<Destroy>", self._on_master_destroy, add="+")
        except Exception:
            # Widget might not support binding destroy (e.g., during teardown); ignore silently.
            pass

    def show(self, text: str, x: int, y: int) -> None:
        if not text.strip():
            self.hide()
            return
        window = self._ensure_window()
        if window is None:
            return
        if text != self._current_text and self._label is not None:
            self._label.config(text=text)
            self._current_text = text
        self._reposition(window, x, y)
        if not self._visible:
            window.deiconify()
            window.lift()
            self._visible = True

    def move(self, x: int, y: int) -> None:
        if not self._visible or self._window is None:
            return
        self._window.geometry(f"+{x}+{y}")

    def hide(self) -> None:
        if not self._visible or self._window is None:
            return
        self._window.withdraw()
        self._visible = False

    def destroy(self) -> None:
        if self._window is not None:
            try:
                self._window.destroy()
            except Exception:
                pass
            finally:
                self._window = None
                self._label = None
                self._visible = False

    def _ensure_window(self) -> Optional[tk.Toplevel]:
        if self._window is not None:
            return self._window
        try:
            window = tk.Toplevel(self.master)
        except Exception:
            return None
        window.withdraw()
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.configure(background=self.background)
        label = tk.Label(
            window,
            text="",
            justify=tk.LEFT,
            background=self.background,
            foreground=self.foreground,
            relief=tk.SOLID,
            borderwidth=1,
            wraplength=self.wraplength,
        )
        label.pack(ipadx=4, ipady=2)
        self._window = window
        self._label = label
        return window

    def _reposition(self, window: tk.Toplevel, x: int, y: int) -> None:
        try:
            width = window.winfo_reqwidth()
            height = window.winfo_reqheight()
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
        except Exception:
            window.geometry(f"+{x}+{y}")
            return

        x_position = min(x, screen_width - width - 10)
        y_position = min(y, screen_height - height - 10)
        window.geometry(f"+{x_position}+{y_position}")

    def _on_master_destroy(self, _event: tk.Event) -> None:
        self.destroy()


@dataclass(frozen=True)
class KeywordHeatmapData:
    sections: List[str]
    keywords: List[str]
    counts: Dict[str, Dict[str, int]]
    totals: Dict[str, int]
    keyword_colors: Dict[str, str]
    max_density: float


__all__ = [
    "TkQueueHandler",
    "AppMetadata",
    "NewsSection",
    "Headline",
    "HeadlineCache",
    "RedisStatistics",
    "HistoricalSnapshot",
    "ArticleContent",
    "SummaryResolution",
    "HeadlineTooltipData",
    "LiveFlowState",
    "HoverTooltip",
    "KeywordHeatmapData",
]


class TkQueueHandler(logging.Handler):
    """Logging handler that forwards formatted records to a Tk callback."""

    def __init__(self, callback: Callable[[int, str], None]) -> None:
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self._callback(record.levelno, message)
        except Exception:  # pragma: no cover - guard against issues
            self.handleError(record)
