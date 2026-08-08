# Changelog

All notable changes to this project should be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com), and this project follows a simple unreleased-first model.

## [Unreleased]

### Fixed
- bounded startup import errors now classify missing non-Tk runtime dependencies (for example `bs4`) instead of surfacing raw `ModuleNotFoundError` during bootstrap
- bootstrap tests now verify the explicit runtime-dependency classification instead of relying on brittle subprocess assumptions about import order

### Added
- Added root `PLAN.md`, `BOUNDS.md`, and a concise `AGENTS.md` contract for bounded, evidence-backed repository work.
- Added canonical product SSOT at `docs/product-ssot.md` for NewsNowNeon operational and quality hardening direction.
- Added `tests/test_newsnow_parsing.py` and a representative HTML fixture to protect section parsing, metadata extraction, deduplication, cutoff handling, limits, and malformed-input behavior.
- Added `tests/test_summary_fallback.py` for cached summaries plus article-fetch and provider fallback contracts.
- Hardened summary resolution against non-string provider output and unexpected provider exceptions.
- Added `tests/test_cache_history.py` with fake-Redis coverage for cache payloads and historical snapshot boundaries.
- Made `load_historical_snapshots(limit=0)` return without scanning or reading Redis.
- Added `tests/test_settings_store.py` for persisted refresh-interval normalization and malformed JSON fallback.
- Normalized persisted `auto_refresh_minutes` to a safe integer range before Tk startup.
- Hardened the active parser path to ignore non-article `javascript:` and `data:` hrefs.
- Added active execution plan at `docs/operational-plan.md` for bounded operational cleanup, CI, and follow-up slices.
- Added minimal GitHub Actions workflow for the frozen pytest gate.
- Added tracked `uv.lock` for reproducible development and CI installs.
- Added pinned Pyright to the retained local quality toolchain.
- Added explicit README / README-DEV pointers to the canonical SSOT.
- Added documented `tkinter` runtime prerequisite and environment-failure guidance.
- Added bounded startup smoke coverage in `tests/test_main_metadata.py` and `tests/test_bootstrap.py`.
- Added a terminal-first `--check` diagnostics path for Python/Tk/display/settings readiness without launching the GUI.
- Added `docs/options-audit.md` to map the operator control surface and recommend a bounded options-clarity slice.
- Added operator-facing wording updates for the controls/options UI so monitoring, refresh, and control-surface labels are clearer without changing behavior.
- Added bounded settings-behavior coverage in `tests/test_settings_behavior.py` for operator-control persistence and normalization paths (visibility state, refresh threshold clamping, exclusions, highlight keywords).
- Added `docs/manual-gui-smoke-checklist.md` so the operator-control wording slice has an explicit GUI verification script for desktop/manual review.

### Changed
- Upgraded pinned GitHub Actions to Node 24-compatible revisions; CI run #31274048561 passed without the deprecated Node 20 annotation.
- Established a minimal operational quality policy: pytest remains the blocking CI gate; Ruff and Pyright remain local baselines for bounded cleanup slices.
- Switched developer and CI installation guidance to frozen `uv.lock` workflows.
- Removed obsolete Black/Mypy configuration and developer-tool references from the active project contract.
- Aligned README, developer guidance, and product SSOT with the current CI/tooling decision.
- Split startup flow in `newsnow_neon.main` into `load_app_class()`, `bootstrap_app()`, and `main()` so dependency failures and bootstrap behavior can be verified without running the full GUI loop.
- Hardened the package front door so `python -m newsnow_neon` and the `__main__` console-script path emit a bounded CLI message when `tkinter` is unavailable, instead of failing with an early import traceback.
- Added subprocess smoke coverage for no-Tk startup on both the module front door and the `__main__` entrypoint path.
- Refreshed the canonical product SSOT so the next planned slice is a diagnostics-first runtime readiness check rather than another broad cleanup pass.
- Implemented `--check` on the supported front doors so startup readiness can be inspected without launching the GUI.
- Turned `--check` into a readiness contract with a final verdict and exit `1` when required launch prerequisites are missing.
- Made the startup seam bind legacy runtime services explicitly from `legacy_app` into `newsnow_neon.app.services` instead of relying only on import-time side effects.
- Made `newsnow_neon.app.controller` resolve exports lazily so importing the package itself no longer pulls Tk-bound controller submodules eagerly.
- Added `newsnow_neon.app.services.__init__` so modular service-provider submodules are now a real importable package surface instead of dead scaffolding.
- Narrowed `newsnow_neon/app/controller.py` to a truthful compatibility alias so it no longer exposes a second `AINewsApp` subclass surface beside the controller package.
