# Changelog

All notable changes to this project should be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com), and this project follows a simple unreleased-first model.

## [Unreleased]

### Added
- Added canonical product SSOT at `docs/product-ssot.md` for NewsNowNeon operational and quality hardening direction.
- Added explicit README / README-DEV pointers to the canonical SSOT.
- Added documented `tkinter` runtime prerequisite and environment-failure guidance.
- Added bounded startup smoke coverage in `tests/test_main_metadata.py` and `tests/test_bootstrap.py`.

### Changed
- Aligned repo documentation around operational polish first: runtime contract, bounded quality cleanup, typed UI/controller seams, and legacy-boundary containment.
- Split startup flow in `newsnow_neon.main` into `load_app_class()`, `bootstrap_app()`, and `main()` so dependency failures and bootstrap behavior can be verified without running the full GUI loop.
