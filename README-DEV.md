# NewsNow Neon – Developer Guide

This document consolidates all developer-facing details for NewsNow Neon. Use it
alongside `README.md`, which remains the user-facing overview.

## Local Environment

```bash
# Install with editable mode plus tooling
pip install -e .[dev]
```

- Python 3.10+ is required.
- Optional extras:
  - `pip install .[redis]` to enable Redis-backed caching (reads `REDIS_URL`).
  - `pip install .[llm]` for LiteLLM-powered summaries.
  - `pip install .[dotenv]` to auto-load `.env` files (`newsnow_neon/config.py#L24`).

## Routine Tooling

```bash
black .
ruff check .
mypy newsnow_neon
pytest -q          # add -vv for verbose test output
python -m newsnow_neon
```

## Entrypoints & Verification

- Desktop launch path:
  - `python -m newsnow_neon` calls `newsnow_neon/__main__._run()`.
  - `_run()` wires through to `newsnow_neon/main.py::main()`.
- `tests/test_main_metadata.py` guards the presence of this wrapper, so keep it
  aligned when editing entrypoints.

## Environment Variables & Settings

- `.env` files load automatically when `python-dotenv` is installed.
- Settings persist at `SETTINGS_PATH` within
  `%LOCALAPPDATA%/NewsNowNeon` (Windows),
  `~/Library/Application Support/NewsNowNeon` (macOS), or
  `~/.config/NewsNowNeon` (Linux). Override with `NEWS_APP_SETTINGS`.

Refer to `README.md` for the comprehensive configuration table that users rely
on; keep that table updated when variables change.

## Change Management

- When modifying user-visible behaviour:
  - Update the relevant sections in `README.md`.
  - Refresh the change log within `newsnow_neon/legacy_app.py`
    (see the `Updates:` block near the top of the module).

## Modularization Notes (v0.53 — 2025-11-18)

The application layer under `newsnow_neon/app/` modularizes services and keeps
the UI controller thin.

- **Services**
  - `newsnow_neon/app/services.py` handles service binding and proxying.
  - Pure helpers live in `filtering`, `rendering`, `timeutils`, and `actions`.
- **Controller**
  - `newsnow_neon/app/controller.py` re-exports the legacy `AINewsApp`.
  - `newsnow_neon/application.py` still implements the concrete controller.
- **Imports**
  - Prefer `from newsnow_neon.app.controller import AINewsApp`.
  - Service binding lives at `newsnow_neon.app.services.configure_app_services`.
- **Public API Signatures**

```python
def configure_app_services(
    *,
    fetch_headlines,
    build_ticker_text,
    resolve_article_summary,
    persist_headlines_with_ticker,
    collect_redis_statistics,
    clear_cached_headlines,
    load_historical_snapshots,
) -> None: ...

def fetch_headlines(*args, **kwargs) -> tuple[list[Headline], bool, str | None]: ...
def build_ticker_text(headlines: Sequence[Headline]) -> str: ...
def resolve_article_summary(headline: Headline) -> object: ...
def persist_headlines_with_ticker(*args, **kwargs) -> None: ...
def collect_redis_statistics() -> RedisStatistics: ...
def clear_cached_headlines() -> tuple[bool, str]: ...
def load_historical_snapshots(*args, **kwargs) -> list[HistoricalSnapshot]: ...
```

Types reference `newsnow_neon/models.py`, and all bindings lean on explicit
dependency injection to satisfy KISS/DRY goals.

## Developer Checklist

1. Keep `README.md` user-focused; place engineering context here.
2. Ensure CI commands (`black`, `ruff`, `mypy`, `pytest`) stay green locally.
3. Use `pip install -e .[dev]` for editable installs with tooling.
4. Document any architecture or behaviour changes in this file plus the legacy
   app change log.
