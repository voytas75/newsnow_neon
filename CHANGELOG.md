# Changelog

All notable changes to this project should be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com), and this project follows a simple unreleased-first model.

## [Unreleased]

### Fixed
- bounded startup import errors now classify missing non-Tk runtime dependencies (for example `bs4`) instead of surfacing raw `ModuleNotFoundError` during bootstrap
- bootstrap tests now verify the explicit runtime-dependency classification instead of relying on brittle subprocess assumptions about import order

### Added
- Added canonical product SSOT at `docs/product-ssot.md` for NewsNowNeon operational and quality hardening direction.
- Added explicit README / README-DEV pointers to the canonical SSOT.
- Added documented `tkinter` runtime prerequisite and environment-failure guidance.
- Added bounded startup smoke coverage in `tests/test_main_metadata.py` and `tests/test_bootstrap.py`.
- Added a terminal-first `--check` diagnostics path for Python/Tk/display/settings readiness without launching the GUI.
- Added `docs/options-audit.md` to map the operator control surface and recommend a bounded options-clarity slice.
- Added operator-facing wording updates for the controls/options UI so monitoring, refresh, and control-surface labels are clearer without changing behavior.
- Added bounded settings-behavior coverage in `tests/test_settings_behavior.py` for operator-control persistence and normalization paths (visibility state, refresh threshold clamping, exclusions, highlight keywords).
- Added `docs/manual-gui-smoke-checklist.md` so the operator-control wording slice has an explicit GUI verification script for desktop/manual review.

### Changed
- Aligned repo documentation around operational polish first: runtime contract, bounded quality cleanup, typed UI/controller seams, and legacy-boundary containment.
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
