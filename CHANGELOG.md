# Changelog

All notable changes to this project should be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com), and this project follows a simple unreleased-first model.

## [Unreleased]

### Added
- Added canonical product SSOT at `docs/product-ssot.md` for NewsNowNeon operational and quality hardening direction.
- Added explicit README / README-DEV pointers to the canonical SSOT.
- Added documented `tkinter` runtime prerequisite and environment-failure guidance.
- Added bounded startup smoke coverage in `tests/test_main_metadata.py` and `tests/test_bootstrap.py`.
- Added a terminal-first `--check` diagnostics path for Python/Tk/display/settings readiness without launching the GUI.

### Changed
- Aligned repo documentation around operational polish first: runtime contract, bounded quality cleanup, typed UI/controller seams, and legacy-boundary containment.
- Split startup flow in `newsnow_neon.main` into `load_app_class()`, `bootstrap_app()`, and `main()` so dependency failures and bootstrap behavior can be verified without running the full GUI loop.
- Hardened the package front door so `python -m newsnow_neon` and the `__main__` console-script path emit a bounded CLI message when `tkinter` is unavailable, instead of failing with an early import traceback.
- Added subprocess smoke coverage for no-Tk startup on both the module front door and the `__main__` entrypoint path.
- Refreshed the canonical product SSOT so the next planned slice is a diagnostics-first runtime readiness check rather than another broad cleanup pass.
- Implemented `--check` on the supported front doors so startup readiness can be inspected without launching the GUI.
