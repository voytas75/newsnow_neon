# NewsNow Neon – Developer Guide

This guide captures the engineering-facing details that complement the user-focused `README.md`. Use it to bootstrap local environments, understand the architecture, and keep workflow conventions aligned with the automation in CI.

Canonical product SSOT: `docs/product-ssot.md`

## Getting Started
1. Ensure Python 3.10+ is available and create a virtual environment.
2. Ensure the local Python runtime includes `tkinter`.
3. Install the project with tooling enabled:
   ```bash
   uv sync --extra dev
   ```
4. (Optional) Add runtime extras as needed:
   ```bash
   uv sync --extra dev --extra redis --extra llm --extra dotenv
   ```
5. Create a `.env` file if you need to pin provider credentials locally (the loader auto-runs when `python-dotenv` is present).

Alternative pip flow:
```bash
pip install -e .[dev]
pip install .[redis,llm,dotenv]  # optional
```

## Tooling & Daily Commands
```bash
uv run black .
uv run ruff check .
uv run mypy newsnow_neon
uv run pytest tests/test_main_metadata.py tests/test_bootstrap.py -q
uv run pytest -q
uv run newsnow-neon
uv run python -m newsnow_neon
uv run newsnow-neon --check
uv run python -m newsnow_neon --check
```
- `pytest --cov` should remain ≥80 % statement coverage; add tests under `tests/` with `test_*` names.
- Run `uv sync --extra dev` before daily work to keep the environment aligned.
- The bounded startup smoke pack is `tests/test_main_metadata.py` + `tests/test_bootstrap.py`.

Alternative direct tool flow in an activated venv:
```bash
black .
ruff check .
mypy newsnow_neon
pytest tests/test_main_metadata.py tests/test_bootstrap.py -q
pytest -q
python -m newsnow_neon
```

## Environment & Secrets
- `.env` files are loaded automatically when `python-dotenv` is installed (see `newsnow_neon/config.py`).
- Settings persist at `SETTINGS_PATH`, which resolves to:
  - Windows: `%LOCALAPPDATA%/NewsNowNeon/ainews_settings.json`
  - macOS: `~/Library/Application Support/NewsNowNeon/ainews_settings.json`
  - Linux: `~/.config/NewsNowNeon/ainews_settings.json`
- Override the settings location with `NEWS_APP_SETTINGS`; `LOCALAPPDATA` and `XDG_CONFIG_HOME` are honoured if set.

## Operator control surface
- The app now treats options as an operator control surface rather than a loose settings bucket.
- Current product-facing control groups are best understood as:
  - **Monitoring** — auto refresh timer, refresh cadence, next/last refresh feedback,
  - **Background Watch** — unseen-headline polling and threshold-triggered refresh,
  - **History & Time** — 24h history retention and display timezone,
  - **Debug & Logs** — debug logging, LiteLLM debug, log visibility,
  - **Appearance & Readability** — theme/profile, custom colors, ticker speed.
- Adjacent triage controls remain outside the main options group but are part of the same effective operator workflow:
  - search,
  - section filter,
  - exclude terms,
  - highlight keywords,
  - mute source / mute keyword actions.
- Canonical audit for this surface: `docs/options-audit.md`.
- Current bounded test coverage for this surface lives in `tests/test_settings_behavior.py` and covers persistence/clamping for visibility, refresh thresholds, exclusions, and highlight keyword controls.
- Manual visual verification checklist for this slice: `docs/manual-gui-smoke-checklist.md`.

### Frequently Tuned Variables
| Variable | Context |
| --- | --- |
| `REDIS_URL` | Enables Redis caching; also unlocks diagnostics and history snapshot UI. |
| `NEWS_CACHE_KEY` / `NEWS_CACHE_TTL` | Primary cache key + TTL; keep in sync with Redis maintenance scripts. |
| `NEWS_HISTORY_PREFIX` / `NEWS_HISTORY_TTL` | Historical snapshot namespace and retention window. |
| `NEWS_SUMMARY_MODEL` / `NEWS_SUMMARY_PROVIDER` | Summary-only LiteLLM overrides for experimentation. |
| `LITELLM_MODEL` / `LITELLM_PROVIDER` / `LITELLM_API_BASE` | Baseline LiteLLM configuration inherited when summary overrides are absent. |
| `NEWS_HIGHLIGHT_KEYWORDS` | `keyword:#HEX` pairs parsed in `newsnow_neon/highlight.py::parse_highlight_keywords()` to drive UI heatmaps. |
| `NEWSNOW_APP_AUTHOR` / `NEWSNOW_DONATE_URL` | Strings surfaced by the Info dialog. |

Sensitive values (`*KEY`, `*TOKEN`, `*SECRET`, `*PASSWORD`) are masked automatically in startup logs, but still store them securely.

## Architecture Overview
- **Entrypoints**: `python -m newsnow_neon` executes `newsnow_neon/__main__._run()`, which delegates to `newsnow_neon/main.py::main()` (guarded by `tests/test_main_metadata.py`). The installed script is `newsnow-neon`; `uv run newsnow_neon` is not a supported invocation.
- **Bootstrap seam**: `newsnow_neon/main.py::load_app_class()` classifies missing Tk support explicitly, and `bootstrap_app()` builds the app before `mainloop()` (guarded by `tests/test_bootstrap.py`).
- **Legacy runtime boundary**: `load_app_class()` now also binds the legacy module's service implementations into `newsnow_neon.app.services` explicitly instead of relying only on import-time side effects.
- **Controller package surface**: `newsnow_neon.app.controller` resolves package exports lazily, and `newsnow_neon/app/controller.py` is now only a truthful compatibility alias for the same `AINewsApp` symbol.
- **Diagnostics seam**: `--check` now renders Python/Tk/display/settings readiness through `newsnow_neon.main` without starting the GUI, and returns a readiness verdict with non-zero exit when required launch prerequisites fail.
- **Next operational seam**: after the first explicit legacy-binding step and lazy controller-package export cleanup, continue with the remaining package-surface cleanup before broader typing work.
- **Application layer**: `newsnow_neon/app/` now exposes a real `services` package surface for modular provider stubs, while the legacy runtime still binds concrete implementations at startup.
- **UI**: `newsnow_neon/ui/` plus `application.py` define Tkinter windows, dialogs, keyword heatmaps, and ticker widgets.
- **Domain models**: Shared dataclasses and helpers live in `models.py`, `cache.py`, `summaries.py`, and `settings_store.py`.
- **Legacy wrapper**: `legacy_app.py` retains the pre-modularized implementation; keep its embedded change log synchronized when behaviour shifts.

## Development Workflow
1. Branch from `main` and sync dependencies (`pip install -e .[dev]`).
2. Implement changes inside `newsnow_neon/` modules, keeping utility code in dedicated modules (KISS/DRY).
3. Add/adjust tests under `tests/`; favour unit tests and keep integration suites under `tests/integration/`.
4. Run `black`, `ruff`, `mypy`, and `pytest -q` before committing. CI runs the same matrix.
5. Update documentation (`README.md`, this guide, and `CHANGELOG.md`) plus docstrings for any public interface changes.

## Troubleshooting & Tips
- **Missing `tkinter`**: install the OS/runtime package for Tk support first (for example `python3-tk` on some Linux distros). Treat missing Tk as environment setup debt, not confirmed app logic failure.
- **Stale Redis data**: Use the UI “Redis Stats” panel or run `redis-cli keys 'news:*'` to verify snapshot churn; `clear_cached_headlines()` is wired via the Diagnostics panel.
- **LLM rate limits**: Adjust `NEWS_SUMMARY_TIMEOUT` and `NEWS_TICKER_TIMEOUT` or switch providers via LiteLLM env vars; enable “LiteLLM Debug” to surface provider traces.
- **Background watchers**: The Background Watch counter uses polling hooks in `application.py`; keep intervals ≥60s to avoid UI jank.
- **Platform paths**: Always prefer `Path` objects when touching filesystem code; config resolution already handles OS differences.

## Change Management
- User-facing changes require README/README-DEV updates plus a `CHANGELOG.md` entry following [Keep a Changelog](https://keepachangelog.com) conventions.
- Update the `Updates:` banner inside `newsnow_neon/legacy_app.py` when tweaking the legacy controller.
- Maintain type hints on all public functions and keep modules ≤2 levels deep per repository guidelines.

Updates: v0.53.0 - 2025-11-24 - Expanded developer onboarding, environment guidance, and workflow expectations.
