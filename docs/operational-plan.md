# NewsNow Neon — Operational Plan

**Status:** active — Stage 1 and Stage 2 verified remotely; governance controls refreshed in this slice.
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

**Status:** implemented and verified remotely by CI run [#31273084062](https://github.com/voytas75/newsnow_neon/actions/runs/31273084062).

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

**Status:** implemented and verified remotely by CI run [#31273084062](https://github.com/voytas75/newsnow_neon/actions/runs/31273084062).

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

### Slice 1C — GitHub Actions Node 24 runtime maintenance

**Status:** completed and verified remotely by CI run [#31274048561](https://github.com/voytas75/newsnow_neon/actions/runs/31274048561).

**Changed:**
- upgraded pinned `actions/checkout` from v4 to v5;
- upgraded pinned `actions/setup-python` from v5 to v6;
- upgraded pinned `astral-sh/setup-uv` from v5 to v9.0.0;
- resolved all three pins from official GitHub tags and inspected each selected
  `action.yml`: each declares `runs.using: node24`.

**Preserved:** `contents: read`, Python 3.11, `uv` 0.8.23, frozen dependency
setup, existing triggers, and the pytest-only CI gate.

**Validation:**
```bash
uv sync --extra dev --frozen
uv run --extra dev --frozen pytest -q
# local YAML parse and assertions for triggers, permissions, SHA pins, inputs,
# and exact gate commands
```

**Remote verification:** CI run [#31274048561](https://github.com/voytas75/newsnow_neon/actions/runs/31274048561) completed successfully; its pytest check run reported zero annotations, and its logs contain no `Node.js 20 is deprecated` message.

## Stage 2 — product behavior confidence

### Slice 2A — NewsNow parsing fixture

**Status:** completed and verified remotely by CI run [#31273084062](https://github.com/voytas75/newsnow_neon/actions/runs/31273084062).

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

**Status:** completed and verified remotely by CI run [#31273084062](https://github.com/voytas75/newsnow_neon/actions/runs/31273084062).

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

#### Slice 2B.3 — summary/provider fallback contracts

**Changed:**
- added `tests/test_summary_fallback.py` with fully mocked cache, article-fetch,
  and provider seams;
- covered primary-URL cache hit, article-fetch failure, missing provider output,
  and unexpected provider exceptions;
- hardened `resolve_article_summary` so a non-string/empty provider result and an
  unexpected provider exception return a usable fallback instead of raising into
  the operator UI.

**Validation:**
```bash
uv run --extra dev --frozen pytest tests/test_summary_fallback.py -q
uv run --extra dev --frozen ruff check tests/test_summary_fallback.py
uv run --extra dev --frozen pyright tests/test_summary_fallback.py
uv run --extra dev --frozen pytest -q
```

**Known baseline:** `newsnow_neon/legacy_app.py` remains a large legacy module
with repository-wide static debt. The new test module is Ruff- and Pyright-clean;
this behavior slice did not undertake monolith cleanup.

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

## Stage 3A — service-surface inventory

**Status:** completed read-only; evidence is recorded in
[`service-surface-inventory.md`](service-surface-inventory.md).

**Confirmed:** normal imports resolve to `app/services/__init__.py`; the
parallel `app/services.py` registry is not selected by internal normal imports.
Direct imports in controllers/UI capture package placeholders before legacy
startup configures the package, and a clean-process probe confirmed that the
stale callable raises `NotImplementedError` after rebinding.

**Outcome:** Stage 3B completed the stable-proxy fix locally without removing or
renaming either compatibility surface.

## Stage 3B — stable service-proxy binding

**Status:** completed locally; remote CI verification pending.

**Changed:** `app/services/__init__.py` now retains stable public proxies and
updates private implementation slots during configuration. Direct imports taken
before startup configuration therefore dispatch correctly afterward.

**Validation:** focused bootstrap/service tests, full frozen pytest, scoped
Ruff, scoped Pyright, and Python compilation all passed. Evidence is in
[`service-proxy-binding.md`](service-proxy-binding.md).

**Next:** P1 is a bounded service-compatibility contract slice following the
completed Stage 3C inventory and P0 policy decision.

## Stage 3C — controller-surface inventory

**Status:** completed read-only at `7c607df`; evidence is recorded in
[`controller-surface-inventory.md`](controller-surface-inventory.md).

**Confirmed:** normal dotted imports select `app/controller/__init__.py`; the
parallel `app/controller.py` is an identity-preserving compatibility file with
no internal normal-import consumer. `application.py` imports and instantiates
the concrete controller submodules directly.

**P0 decision:** retain `controller.py` and `services.py` as supported external
compatibility surfaces. `controller.py` already has a focused identity test; P1
subsequently aligned the separate `services.py` file-path registry with
canonical package-proxy behavior.

## P1 — service compatibility contract

**Status:** completed locally at `5ea9da3`.

**Changed:** replaced the separate `services.py` registry with a compatibility
re-export of the canonical stable package proxies, without changing public
service names.

**Validation:** `tests/test_service_bindings.py` establishes RED for an
explicit file-path module load, then proves its captured `fetch_headlines`
dispatches after canonical package configuration. Focused pytest, scoped Ruff,
scoped Pyright, bytecode compilation, and the full frozen pytest suite passed.

**Next:** Stage 4 must select one behavior-owned static-debt seam.

## Security lock refresh

**Status:** completed and verified remotely by CI run [#31278999184](https://github.com/voytas75/newsnow_neon/actions/runs/31278999184).

**Changed:** refreshed only `aiohttp` (3.13.5 → 3.14.3) and `soupsieve`
(2.8.3 → 2.9.2) in `uv.lock`, addressing the two transitive package paths
behind all 16 open alerts.

**Validation:** `uv lock --check`, frozen sync with `dev` and `llm` extras,
version imports, and the full pytest suite passed. The measured static baseline
and security closure result are in
[`quality-security-backlog.md`](quality-security-backlog.md).

**Remote result:** GitHub's Dependency Graph submitted the refreshed versions,
and Dependabot reports zero open alerts; all 16 prior alerts are fixed.

## Current doubts / to verify

- Whether Python 3.11 is the right single CI runtime versus adding a later
  compatibility matrix.
- How the 16 open Dependabot alerts should be prioritized after CI runtime
  maintenance (3 high, 9 moderate, 4 low).
- Whether external users depend on the compatibility module/package aliases.

## Current recommended next execution slice

**Begin Stage 4 as a bounded static-debt reduction slice.** Select one
behavior-owned seam, establish its quality baseline, and reduce only directly
owned Ruff/Pyright debt with focused regression coverage.
