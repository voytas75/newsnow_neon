# NewsNowNeon

NewsNowNeon is a Tkinter desktop dashboard that surfaces curated NewsNow headlines, caches LiteLLM summaries, and exposes live controls for refresh intervals, Redis usage, and observability.

Canonical product SSOT: `docs/product-ssot.md`

## Installation

- Requires Python 3.11+.
- Requires a desktop Python build with `tkinter` available.
- On some Linux distributions this means installing the OS package separately (for example `python3-tk`).

### Project `.venv` with uv (recommended)

Run from the repository root. `uv sync` creates or updates the project's `.venv`;
all subsequent `uv run` commands use that environment.

```bash
uv sync --extra dev --frozen
```

For a minimal runtime environment:

```bash
uv sync --frozen
```

### Direct virtual-environment flow

If you do not use `uv`, create and target the project `.venv` explicitly. Do not
run bare `pip install ...`, because it may target a host Python instead.

```bash
python -m venv .venv
source .venv/bin/activate  # POSIX shells; PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

# Optional runtime extras
python -m pip install ".[redis,llm,dotenv]"
```

## Quick Start
```bash
# Create/update the project .venv from the locked development environment.
uv sync --extra dev --frozen

# Configure environment (examples)
export NEWS_SUMMARY_MODEL=gpt-4.1
export NEWS_TICKER_TIMEOUT=15
# export REDIS_URL=redis://localhost:6379/0

# Run the desktop app from the project .venv.
uv run --frozen newsnow-neon       # installed console script
uv run --frozen python -m newsnow_neon  # module entrypoint

# Check launch readiness without starting the GUI.
uv run --frozen newsnow-neon --check
uv run --frozen python -m newsnow_neon --check
```

Direct `.venv` alternatives (POSIX; activate first or call the executable path):
```bash
source .venv/bin/activate
python -m newsnow_neon

# Equivalent without activation
.venv/bin/newsnow-neon
.venv/bin/python -m newsnow_neon
```

- `.env` files are auto-loaded when `python-dotenv` is installed (see `newsnow_neon/config.py`).
- Settings persist at the platform-specific path resolved by `NEWS_APP_SETTINGS` (default shown below).
- Canonical runtime entrypoints: `python -m newsnow_neon` and the installed script `newsnow-neon`.
- Startup now uses a bounded bootstrap seam in `newsnow_neon.main` before entering `mainloop()`.
- Use `--check` on either supported front door to inspect Python/Tk/display/settings readiness without launching the GUI.
- `--check` now ends with a readiness verdict and returns exit `1` when required launch prerequisites are missing.
- If startup fails with `RuntimeError: Tkinter is not available...`, fix the OS/runtime dependency first; treat that as an environment issue, not as confirmed app regression.
- If startup fails in a headless shell with no GUI display, the CLI now prints a short terminal message instead of a raw Tk traceback.

## Features
- **Aggregated headlines** – Scrapes multiple NewsNow sections into a scrolling ticker and grouped headline list.
- **Cached summaries** – LiteLLM summaries can be persisted in the optional Redis cache for reuse; without Redis, the app falls back to in-memory operation.
- **Rich preferences** – Colour profiles, ticker speed, geometry, logging flags, and keyword highlights survive restarts.
- **Redis insights** – Optional Redis integration exposes diagnostics, cache persistence, and history snapshots.
- **Observability toggles** – Enable debug logging, LiteLLM verbosity, keyword heatmaps, and info dialogs without restarts.

## Current focus
- **Operational trust first** – startup/runtime failures should classify cleanly instead of failing with raw tracebacks.
- **Supported compatibility surfaces** – `controller.py` and `services.py` remain supported externally; explicit `services.py` file-path loads now use the canonical package proxies.
- **GUI-first acceptance** – controlled real-Tk coverage now spans Stage 4L–12, including rendering, refresh, filtering, exclusions, summaries, highlights, persisted controls, cache clear, Info, selected-row mute actions, History 24h, and Redis Stats. The active next decision is to select one still-unverified operator workflow; no live NewsNow, Redis, or provider acceptance is implied.

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
# Reproducible developer and CI setup
uv sync --extra dev --frozen

# Required CI gate
uv run --extra dev --frozen pytest -q

# Retained local quality baselines
uv run --extra dev --frozen ruff check .
uv run --extra dev --frozen pyright
```

Direct project-`.venv` alternative (POSIX):
```bash
source .venv/bin/activate
python -m pytest -q
ruff check .
pyright
```

Without activation, use `.venv/bin/pytest`, `.venv/bin/ruff`, and
`.venv/bin/pyright` explicitly.

GitHub Actions requires the full pytest suite on pushes and pull requests to
`main`. Ruff and Pyright remain local quality tools while their existing
repo-wide diagnostic debt is reduced through bounded slices.

## Developer

- Deep dive: [README-DEV.md](README-DEV.md)
- Operational execution history: [docs/operational-plan.md](docs/operational-plan.md)
- Product direction SSOT: [docs/product-ssot.md](docs/product-ssot.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)

## License
[MIT](LICENSE)

Updates: v0.53.0 - 2026-08-09 - Current delivery state and GUI-acceptance boundaries synchronized with the product SSOT.
