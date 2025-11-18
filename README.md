# NewsNow Neon Desktop

NewsNow Neon is a Tkinter desktop dashboard that surfaces curated NewsNow
headlines, enriched with cached summaries and live configuration controls.
It is packaged as a Python module and can be launched via:

```bash
python -m newsnow_neon
```

This aligns with [__main__._run()](newsnow_neon/__main__.py#L17) and the entry
wiring in [main.main()](newsnow_neon/main.py#L35).

## Feature Highlights

- **Headline aggregation** – Scrapes multiple NewsNow sections and interleaves
  them in a scrolling ticker plus sortable list.
- **Offline-aware summaries** – Article text is fetched with resilient retry
  logic, summarised through LiteLLM, and cached (alongside fallbacks) for
  offline reuse.
- **Redis-backed caching** – Optional Redis storage keeps headlines, ticker
  text, and summaries warm between sessions.
- **Redis diagnostics** – Use the “Redis Stats” button to review cache TTL, payload
  size, snapshot counts, and server health details sourced directly from Redis.
- **Historical snapshots** – Keep a rolling 24-hour Redis history (keys such as
  `news:YYYY-MM-DD:*`) to replay recent headline states; toggle it from the
  settings panel.
- **Configurable auto-refresh** – Headlines refresh automatically every five
  minutes by default; toggle or adjust the interval directly from the settings
  panel, complete with a live countdown to the next refresh.
- **Background watch counter** – Enable the new checkbox in the Behavior &
  Timing panel to poll for unseen headlines in the background and surface how
  many fresh articles are waiting outside the current list.
- **User preferences** – Colour profiles, ticker speed, window geometry,
  logging visibility, and LiteLLM debug flags persist in
  `%LOCALAPPDATA%/NewsNowNeon/ainews_settings.json` (override with
  `NEWS_APP_SETTINGS`).
- **Observability controls** – Separate checkboxes let you toggle Python debug
  logging and LiteLLM verbose output while the app is running.
- **Keyword heatmap** – Launch the “Keyword Heatmap” window to compare how often
  highlighted terms appear across sections; intensity is scaled to per-section
  headline density.
- **Info dialog** – Tap the “Info” button for a quick snapshot of version,
  system details, author attribution (defaults to `https://github.com/voytas75`),
  and the support link (defaults to `https://ko-fi.com/voytas`).
- **Keyword exclusions** – Enter comma-separated terms to hide matching
  headlines across tickers and list views without mutating cached data.

## Running the App

```bash
python -m newsnow_neon
```

## Installation

- Requires Python 3.10+.

- Editable dev install (linters, mypy, pytest included):
```bash
pip install -e .[dev]
```

- Minimal runtime install:
```bash
pip install .
```

- Optional extras:
```bash
# Redis cache via [REDIS_URL](newsnow_neon/config.py#L86)
pip install .[redis]

# LiteLLM-based summaries
pip install .[llm]

# Auto-load .env (see [dotenv load](newsnow_neon/config.py#L24))
pip install .[dotenv]
```

The module auto-loads a `.env` file when `python-dotenv` is installed; see
[config.py](newsnow_neon/config.py#L24).

## Optional Environment Variables

| Variable | Purpose |
| --- | --- |
| `NEWS_SUMMARY_TIMEOUT` | Seconds before LiteLLM article summarisation aborts (min 5, default 15). |
| `NEWS_TICKER_TIMEOUT` | Legacy ticker LLM timeout; kept for backwards compatibility (min 3, default 8). |
| `NEWS_CACHE_KEY` / `NEWS_CACHE_TTL` | Redis key name and TTL (defaults: `ainews:headlines:v1`, 900s). |
| `NEWS_HISTORY_PREFIX` / `NEWS_HISTORY_TTL` | Redis prefix and TTL for historical snapshots (defaults: `news`, 86400s). |
| `REDIS_URL` | Enables Redis caching when set (e.g. `redis://localhost:6379/0`). See [REDIS_URL](newsnow_neon/config.py#L86). |
| `NEWS_APP_SETTINGS` | Custom path for the persisted settings JSON; overrides [SETTINGS_PATH](newsnow_neon/config.py#L200). |
| `NEWS_HIGHLIGHT_KEYWORDS` | Custom highlight rules in the format `keyword:#HEX; term2:#HEX`. Parsed by [parse_highlight_keywords()](newsnow_neon/highlight.py#L46). |
| `NEWS_SUMMARY_MODEL` / `NEWS_SUMMARY_PROVIDER` / `NEWS_SUMMARY_API_*` | Override the LiteLLM model/provider/base/key used exclusively for article summaries. |
| `NEWS_SUMMARY_AZURE_*` | Azure-specific overrides for summaries (deployment, API version, AD token). |
| `LITELLM_MODEL` / `LITELLM_PROVIDER` / `LITELLM_API_BASE` / `LITELLM_API_KEY` | Default LiteLLM configuration when summary-specific overrides are absent. |
| `AZURE_OPENAI_*` | Generic Azure OpenAI deployment/API/key overrides shared across LiteLLM calls (API base may be `AZURE_OPENAI_API_BASE` or `AZURE_OPENAI_ENDPOINT`). |
| `XDG_CONFIG_HOME` | Linux/macOS: overrides the base config directory (defaults to `~/.config` on Linux, `~/Library/Application Support` on macOS). |
| `LOCALAPPDATA` | Windows-only: used to locate the settings directory. Ignored on Linux/macOS. |
| `NEWSNOW_APP_AUTHOR` | Overrides the author string surfaced by the Info dialog (defaults to `https://github.com/voytas75`). |
| `NEWSNOW_DONATE_URL` | URL opened from the Info dialog “Support” link (defaults to `https://ko-fi.com/voytas`). |

> ⚠️ Keys or tokens are never emitted to logs. The app masks any variable whose
> name ends in `KEY`, `TOKEN`, `SECRET`, or `PASSWORD` (as well as known Azure
> variants) when printing the startup configuration report.

## Settings storage

- Default settings file location depends on OS (resolved by
  [SETTINGS_PATH](newsnow_neon/config.py#L200)):
  - Windows: `%LOCALAPPDATA%/NewsNowNeon/ainews_settings.json`
  - macOS: `~/Library/Application Support/NewsNowNeon/ainews_settings.json`
  - Linux: `~/.config/NewsNowNeon/ainews_settings.json`
- Override the location with `NEWS_APP_SETTINGS`.
- Resolution logic uses `LOCALAPPDATA`/`XDG_CONFIG_HOME` as shown in
  [config.py](newsnow_neon/config.py#L176).

## Development

```bash
# one‑liner dev setup (formatters, linters, tests)
pip install -e .[dev]

# formatting & static analysis
black .
ruff check .
mypy newsnow_neon

# run the desktop app
python -m newsnow_neon

# execute test suite
pytest -q          # add -vv for verbose output
```

Entrypoint wiring is defined in [__main__._run()](newsnow_neon/__main__.py#L17)
which calls [main.main()](newsnow_neon/main.py#L35). The presence of this wrapper
is validated in [tests/test_main_metadata.py](tests/test_main_metadata.py#L49).

- Whenever you change user-visible behaviour, update both this README and the
  change log in [newsnow_neon/legacy_app.py](newsnow_neon/legacy_app.py)
  (see the `Updates:` section near the top of that module).

## Troubleshooting

- **403/429 summaries** – Retry logic automatically cycles through alternate
  headers and fallback user agents; final errors surface as cached or headline
  snippets instead of raising.
- **No Redis** – Leave `REDIS_URL` unset to run in purely in-memory mode; the
  UI will display “Redis: OFF”.
- **Verbose LLM traces** – Tick “LiteLLM Debug” in the settings panel to enable
  provider-specific logging without restarting the app.
- **Auto refresh timing** – Use the “Auto Refresh” checkbox and interval spinbox
  to tweak how often headlines update (minimum 1 minute) and watch the
  countdown for the next update.

## Quick Start

```bash
# Install with developer tooling
pip install -e .[dev]

# Example environment variables
export NEWS_SUMMARY_MODEL=gpt-4.1
export NEWS_TICKER_TIMEOUT=15
# Optional Redis cache
# export REDIS_URL=redis://localhost:6379/0

# Run the desktop app
python -m newsnow_neon
```

Notes:
- If [python-dotenv](pyproject.toml) is installed, a `.env` file will be
  auto-loaded during startup (see [newsnow_neon/config.py](newsnow_neon/config.py#L24)).
- Settings are persisted at
  [SETTINGS_PATH](newsnow_neon/config.py#L200). Override with `NEWS_APP_SETTINGS`.

## License

See [LICENSE](LICENSE).

## Modularization Update (v0.52 — 2025-11-18)

This release introduces a modular application layer under `newsnow_neon/app/` to improve separation of concerns, testability, and readability while preserving backward compatibility.

### What changed

- New app package:
  - `newsnow_neon/app/services.py` — service injection and proxies (central binding point).
  - `newsnow_neon/app/filtering.py` — pure headline filtering and exclusion normalization.
  - `newsnow_neon/app/timeutils.py` — timezone coercion and localized timestamp formatting.
  - `newsnow_neon/app/rendering.py` — age grouping, relative-age labels, metadata composition.
  - `newsnow_neon/app/actions.py` — “mute keyword/source” derivation helpers.
  - `newsnow_neon/app/controller.py` — modular wrapper re-exporting the legacy controller.
- Existing controller remains in `newsnow_neon/application.py` for compatibility; it now uses the modular service layer for bindings.
- No breaking API changes; legacy imports continue to work.

### Recommended imports (new modular path)

```python
from newsnow_neon.app.services import configure_app_services  # service binding
from newsnow_neon.app.controller import AINewsApp            # controller

# Bind your services (examples shown as placeholders):
configure_app_services(
    fetch_headlines=...,
    build_ticker_text=...,
    resolve_article_summary=...,
    persist_headlines_with_ticker=...,
    collect_redis_statistics=...,
    clear_cached_headlines=...,
    load_historical_snapshots=...,
)

# Launch the UI
AINewsApp().mainloop()
```

### Backward compatibility (legacy path remains valid)

```python
# Still supported:
from newsnow_neon.application import configure_app_services, AINewsApp
```

### Public function signatures (current state)

```python
# Bindings
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

# Proxies (identical behavior as before)
def fetch_headlines(*args, **kwargs) -> tuple[list[Headline], bool, str | None]: ...
def build_ticker_text(headlines: Sequence[Headline]) -> str: ...
def resolve_article_summary(headline: Headline) -> object: ...
def persist_headlines_with_ticker(*args, **kwargs) -> None: ...
def collect_redis_statistics() -> RedisStatistics: ...
def clear_cached_headlines() -> tuple[bool, str]: ...
def load_historical_snapshots(*args, **kwargs) -> list[HistoricalSnapshot]: ...
```

Types referenced:
- `Headline`, `HistoricalSnapshot`, `RedisStatistics` from `newsnow_neon/models.py`.
- `Sequence` from `typing`.

### Architecture overview

- Controller:
  - `newsnow_neon/app/controller.py` re-exports the legacy `AINewsApp` as the modular import path.
  - `newsnow_neon/application.py` remains the concrete controller implementation and UI wiring.
- Services:
  - `newsnow_neon/app/services.py` is the sole binding/proxy location. This keeps injection explicit and discoverable.
- Pure helpers:
  - `filtering`, `rendering`, `timeutils`, `actions` contain focused, UI-agnostic logic for easy unit testing.
- Views:
  - `newsnow_neon/ui.py` remains unchanged and continues to host `NewsTicker`, `KeywordHeatmapWindow`, `AppInfoWindow`, `RedisStatsWindow`, `SummaryWindow`.

### Migration notes for developers

- New code should import the controller from `newsnow_neon.app.controller` and bind services via `newsnow_neon.app.services`.
- Existing code importing from `newsnow_neon.application` continues to work; gradual migration is optional.
- When adding new pure logic, prefer placing it in the relevant module under `newsnow_neon/app/` to keep the controller thin.
- The modularization follows KISS/DRY and prepares the codebase for targeted unit tests of pure functions.
