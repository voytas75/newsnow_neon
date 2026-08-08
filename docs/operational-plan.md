# NewsNow Neon — Operational Plan

**Status:** active
**Updated:** 2026-08-08
**Canonical product direction:** [`product-ssot.md`](product-ssot.md)

## Goal

Bring the repository to a controlled operational baseline without expanding
product scope: deterministic local setup, one minimal remote CI gate, explicit
quality-tool policy, and bounded follow-up slices.

## Confirmed current state

- Repository: `/home/voytas/projects/newsnow_neon`.
- Branch `main` is clean and exactly aligned with `origin/main` at the start of
  this plan.
- Full local `pytest -q` passes.
- `newsnow-neon --check` passes in the current WSL desktop-capable environment.
- Retained tools: `pytest`, Ruff, and Pyright.
- Black and Mypy were removed from the declared development toolchain because
  they are not part of the chosen project policy.
- Baseline measurements before cleanup:
  - Ruff: 1,174 repository-wide diagnostics.
  - Pyright: 638 errors and 15 warnings repository-wide.
- No project-owned GitHub Actions quality workflow existed before this slice.

## Decision

Use **pytest as the only blocking CI gate for now**. Keep Ruff and Pyright as
required local quality tools and measure them in bounded scopes. Do not add a
known-red repository-wide Ruff or Pyright job to CI. Promote a bounded Ruff or
Pyright scope to CI only after it is green and has an explicit ownership
boundary.

## Stage 1 — operational baseline

### Slice 1A — toolchain and lockfile

**Status:** implemented locally; verification pending.

**Changed:**
- `pyproject.toml` retains `pytest`, Ruff, and pinned `pyright` in `dev`.
- Black and Mypy are removed from dev dependencies and tool configuration.
- `uv.lock` is generated and tracked for frozen installs.
- `.gitignore` allows the tracked lockfile.
- `README.md`, `README-DEV.md`, `AGENTS.md`, and the product SSOT state the
  selected quality policy.

**Validation:**
```bash
uv lock --check
uv run --extra dev --frozen pytest -q
uv run --extra dev --frozen ruff check .
uv run --extra dev --frozen pyright
```

**Done condition:** pytest remains green; Ruff and Pyright baseline failures are
recorded, not silently presented as CI regressions.

### Slice 1B — minimal GitHub CI

**Status:** implemented locally; remote verification pending.

**Changed:**
- `.github/workflows/ci.yml`
- one `pytest` job on pushes and pull requests to `main`;
- Python 3.11, pinned `uv` action/runtime, frozen `uv.lock` install;
- read-only repository permissions.

**Validation:**
```bash
# local contract
uv sync --extra dev --frozen
uv run --extra dev --frozen pytest -q

# after push
# gh run list --repo voytas75/newsnow_neon --workflow CI --limit 3
```

**Done condition:** the Actions run for the new commit is completed/success.

## Stage 2 — product behavior confidence

### Slice 2A — NewsNow parsing fixture

**Status:** completed locally; remote CI verification pending.

**Changed:**
- added `tests/fixtures/newsnow_section.html` with representative legacy and
  article-card markup;
- added `tests/test_newsnow_parsing.py` covering metadata, deduplication,
  cutoff handling, item limits, and empty/malformed markup;
- hardened the active parser path to ignore `javascript:` and `data:` hrefs.

**Validation:**
```bash
uv run --extra dev --frozen pytest tests/test_newsnow_parsing.py -q
uv run --extra dev --frozen ruff check tests/test_newsnow_parsing.py
uv run --extra dev --frozen pyright tests/test_newsnow_parsing.py
uv run --extra dev --frozen pytest -q
```

**Done condition:** core section parsing is protected without GUI, Redis,
LiteLLM, or live NewsNow access.

### Slice 2B — settings/cache/fallback contracts

**Status:** settings and cache/history sub-slices completed locally; summary
fallback remains pending.

#### Slice 2B.1 — settings load normalization

**Changed:**
- `newsnow_neon/settings_store.py` now normalizes persisted
  `auto_refresh_minutes` to an integer in `1..180`;
- malformed, boolean, non-numeric, and out-of-range values fall back safely;
- added `tests/test_settings_store.py` for normalization and malformed JSON;
- existing settings round-trip coverage continues to verify known-key filtering.

**Validation:**
```bash
uv run --extra dev --frozen pytest tests/test_settings_store.py -q
uv run --extra dev --frozen ruff check tests/test_settings_store.py newsnow_neon/settings_store.py
uv run --extra dev --frozen pyright tests/test_settings_store.py newsnow_neon/settings_store.py
uv run --extra dev --frozen pytest -q
```

#### Slice 2B.2 — offline cache/history payload contracts

**Changed:**
- added `tests/test_cache_history.py` using an in-memory Redis subset;
- covered zero-limit behavior, horizon filtering, newest-first limit handling,
  invalid historical keys, malformed JSON, and primary-cache metadata retention;
- made `load_historical_snapshots(limit=0)` return immediately without scanning
  or reading Redis.

**Validation:**
```bash
uv run --extra dev --frozen pytest tests/test_cache_history.py -q
uv run --extra dev --frozen ruff check tests/test_cache_history.py
uv run --extra dev --frozen pyright tests/test_cache_history.py newsnow_neon/cache.py
uv run --extra dev --frozen pytest -q
```

**Known baseline:** `newsnow_neon/cache.py` has 59 pre-existing repository-style
Ruff diagnostics. They are outside this behavior slice; the new test module is
Ruff-clean and the cache seam is Pyright-clean.

**Next:** execute the summary/provider fallback test seam in a separate bounded
step.

## Stage 3 — package-boundary cleanup

### Slice 3A — service surface

Resolve the coexistence of `newsnow_neon/app/services.py` and
`newsnow_neon/app/services/`. Preserve the working runtime rebinding contract
until replacement tests prove the new boundary.

### Slice 3B — controller surface

Resolve or explicitly deprecate `newsnow_neon/app/controller.py` beside the
`app/controller/` package. Keep compatibility only where an actual import
consumer is verified.

**Stop condition:** no deletion of compatibility surfaces without a test or
repository search showing that the supported path remains intact.

## Stage 4 — bounded Ruff/Pyright recovery

Work by seam, not by repository-wide autofix.

Priority order:
1. parser/news service seam;
2. pure filtering/time/rendering helpers;
3. service registry and bootstrap contracts;
4. controller/view seams;
5. legacy GUI module last.

For each slice:
- change behavior only when required by the typed/lint contract;
- add or preserve focused tests;
- run `pytest -q`;
- run Ruff and Pyright on the touched scope;
- record the remaining baseline debt.

**Do not:** use blanket `# type: ignore`, disable broad Ruff/Pyright rules, or
format the entire repository as part of an unrelated behavior slice.

## Standard validation loop

```bash
uv sync --extra dev --frozen
uv run --extra dev --frozen pytest -q
uv run --extra dev --frozen ruff check <touched-files-or-scope>
uv run --extra dev --frozen pyright <touched-files-or-scope>
uv run newsnow-neon --check
```

## Risks and stop conditions

- GUI behavior remains only partially verified in WSL; use a desktop smoke pass
  before claiming full user-facing readiness.
- Live NewsNow markup and provider behavior are external; fixture tests are the
  baseline, not proof of current live availability.
- The legacy runtime is large. Stop a cleanup slice if it starts changing
  multiple unrelated controllers or UI surfaces.
- Do not make Ruff/Pyright blocking until their selected scope is green and
  reproducible under frozen CI installation.

## Current doubts / to verify

- Whether GitHub Actions accepts the pinned action SHAs and the selected uv
  version without a platform-side failure.
- Whether Python 3.11 is the right single CI runtime versus adding a later
  compatibility matrix.
- Which parser seam can be tested with the smallest fixture and no live calls.
- Whether external users depend on the compatibility module/package aliases.

## Current recommended next execution slice

**Execute the final 2B sub-slice: summary/provider fallback contracts.** Keep
provider calls mocked; cover article-fetch and empty-summary failure paths while
preserving parser, settings, and cache/history tests.
