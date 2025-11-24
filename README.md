# NewsNowNeon

NewsNowNeon is a Tkinter desktop dashboard that surfaces curated NewsNow headlines, caches LiteLLM summaries, and exposes live controls for refresh intervals, Redis usage, and observability.

## Installation

- Requires Python 3.10+.
- Editable developer install (recommended):
```bash
pip install -e .[dev]
```
- Minimal runtime install:
```bash
pip install .
```
- Optional extras:
```bash
pip install .[redis]   # Redis-backed caching (reads REDIS_URL)
pip install .[llm]     # LiteLLM-powered summaries
pip install .[dotenv]  # Auto-load .env via python-dotenv
```

## Quick Start
```bash
# Dev installation
pip install -e .[dev]

# Configure environment (examples)
export NEWS_SUMMARY_MODEL=gpt-4.1
export NEWS_TICKER_TIMEOUT=15
# export REDIS_URL=redis://localhost:6379/0    # optional cache backend

# Launch the desktop app
python -m newsnow_neon
```
Notes:
- `.env` files are auto-loaded when `python-dotenv` is installed (see `newsnow_neon/config.py`).
- Settings persist at the platform-specific path resolved by `NEWS_APP_SETTINGS` (default shown below).

## Features
- **Aggregated headlines** – Scrapes multiple NewsNow sections into a scrolling ticker plus sortable list.
- **Cached summaries** – LiteLLM summaries persist locally/Redis for reuse and offline access.
- **Rich preferences** – Colour profiles, ticker speed, geometry, logging flags, and keyword highlights survive restarts.
- **Redis insights** – Optional Redis integration exposes diagnostics, history snapshots, and cache warmers.
- **Observability toggles** – Enable debug logging, LiteLLM verbosity, keyword heatmaps, and info dialogs without restarts.

## Configuration
| Variable | Purpose |
| --- | --- |
| `NEWS_SUMMARY_TIMEOUT` | Seconds before LiteLLM article summarisation aborts (min 5, default 15). |
| `NEWS_TICKER_TIMEOUT` | Legacy ticker LLM timeout; kept for backwards compatibility (min 3, default 8). |
| `NEWS_CACHE_KEY` / `NEWS_CACHE_TTL` | Redis key name and TTL (defaults: `ainews:headlines:v1`, 900s). |
| `NEWS_HISTORY_PREFIX` / `NEWS_HISTORY_TTL` | Redis prefix and TTL for historical snapshots (defaults: `news`, 86400s). |
| `REDIS_URL` | Enables Redis caching when set (e.g. `redis://localhost:6379/0`). |
| `NEWS_APP_SETTINGS` | Custom path for the persisted settings JSON. |
| `NEWS_HIGHLIGHT_KEYWORDS` | `keyword:#HEX; term2:#HEX` rules parsed by `newsnow_neon/highlight.py::parse_highlight_keywords()`. |
| `NEWS_SUMMARY_MODEL` / `NEWS_SUMMARY_PROVIDER` / `NEWS_SUMMARY_API_*` | Override LiteLLM summary model/provider/base/key. |
| `NEWS_SUMMARY_AZURE_*` | Azure-specific overrides for summaries (deployment, API version, AD token). |
| `LITELLM_MODEL` / `LITELLM_PROVIDER` / `LITELLM_API_BASE` / `LITELLM_API_KEY` | Default LiteLLM configuration when summary overrides are absent. |
| `AZURE_OPENAI_*` | Generic Azure OpenAI deployment/API/key overrides shared across LiteLLM calls. |
| `XDG_CONFIG_HOME` | Linux/macOS config base override (default `~/.config` / `~/Library/Application Support`). |
| `LOCALAPPDATA` | Windows config base override. |
| `NEWSNOW_APP_AUTHOR` | Author string displayed by the Info dialog (defaults to `https://github.com/voytas75`). |
| `NEWSNOW_DONATE_URL` | Support link opened from the Info dialog (defaults to `https://ko-fi.com/voytas`). |

> ⚠️ Keys/tokens are never logged. Any variable ending with `KEY`, `TOKEN`, `SECRET`, or `PASSWORD` (plus known Azure variants) is masked in startup reports.

### Settings Storage
- Windows: `%LOCALAPPDATA%/NewsNowNeon/ainews_settings.json`
- macOS: `~/Library/Application Support/NewsNowNeon/ainews_settings.json`
- Linux: `~/.config/NewsNowNeon/ainews_settings.json`
- Override via `NEWS_APP_SETTINGS`; resolution honours `LOCALAPPDATA`/`XDG_CONFIG_HOME`.

## Troubleshooting
- **403/429 summaries** – Retry logic cycles user agents and falls back to cached snippets instead of raising.
- **Redis disabled** – Leave `REDIS_URL` unset to run entirely in-memory; the UI will show “Redis: OFF”.
- **Verbose LLM traces** – Toggle “LiteLLM Debug” in Settings to enable provider-specific logging without restarting.
- **Auto refresh timing** – Use the “Auto Refresh” checkbox + interval spinner to control refresh cadence (minimum 1 minute).

## Build, Test & Development
```bash
# one-liner dev setup
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

## Developer
- Deep dive: [README-DEV.md](README-DEV.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)

## License
[MIT](LICENSE)

Updates: v0.53.0 - 2025-11-24 - README reorganized, configuration table refreshed, and troubleshooting details aligned with repo guidelines.
