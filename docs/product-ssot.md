# NewsNowNeon Product SSOT

Status: active  
Canonical file: `docs/product-ssot.md`  
Updated: 2026-08-09

## Purpose

This document is the single source of truth for NewsNowNeon product direction, operational hardening priorities, and ordered execution focus.

It governs and should stay aligned with:
- `README.md`
- `README-DEV.md`
- `CHANGELOG.md`
- `pyproject.toml`

When repo-facing docs drift, this file wins and the others should be synced to it.

## Product definition

NewsNowNeon is a desktop operator tool for curated NewsNow headline monitoring with:
- headline aggregation,
- ticker and list-based triage,
- cached article summaries,
- persistent desktop settings,
- optional Redis-backed cache/history/diagnostics.

It is not:
- a generic LLM workstation,
- a workflow orchestrator,
- a backend-first service,
- a broad automation platform.

Primary product center:
- **fast desktop monitoring and triage of curated headlines**.

Supporting layers:
- **operational trust** — predictable startup, readable diagnostics, explicit environment requirements.
- **engineering maintainability** — bounded seams, safe refactors, trustworthy verification.

## Confirmed current baseline

Confirmed from live repo/runtime checks in this cycle:
- package/version in `pyproject.toml`: `0.53.0`
- canonical runtime entrypoints:
  - `python -m newsnow_neon`
  - installed script `newsnow-neon`
- `uv run newsnow_neon` is not a supported invocation
- current test baseline: `pytest -q` passing locally
- startup contract is now hardened across real front doors:
  - `python -m newsnow_neon` without `tkinter` prints a bounded CLI message instead of an early traceback
  - `uv run newsnow-neon` in a headless GUI-less environment prints a bounded display message instead of a raw Tk traceback
- diagnostics path exists:
  - `python -m newsnow_neon --check`
  - `newsnow-neon --check`
- diagnostics currently report:
  - Python version
  - app version
  - Tkinter availability
  - display availability
  - settings path writability
- subprocess smoke coverage exists for:
  - module front door without `tkinter`
  - `__main__` / console-script path without `tkinter`
  - `--check` avoiding GUI launch
- **Current quality contract:** `pytest`, Ruff, and Pyright are retained.
- `pytest` is the current blocking CI gate.
- Ruff and Pyright remain measured local baselines until bounded cleanup slices
  make selected scopes green.
- Black and Mypy are no longer declared project dev tools.

Interpretation:
- the app now has a materially more trustworthy startup/runtime contract,
- but broader maintainability and legacy-boundary work still remain,
- and diagnostics now provide a bounded readiness contract for required launch prerequisites.

## Review-driven gaps and empty areas

These came out of the bounded repo review and should drive the next planning cycle.

### Potwierdzone gaps

1. **Diagnostics semantics beyond the current contract are incomplete**
   - `--check` now produces a readiness verdict and non-zero exit for failed required prerequisites.
   - What remains open is whether optional integrations (for example Redis/LLM state) should join the same contract now or later.
   - The current v1 contract is intentionally limited to launch-critical prerequisites.

2. **Legacy boundary is still only partially explicit**
   - `load_app_class()` now binds runtime services explicitly through `configure_legacy_runtime_services()`.
   - The app class still comes from `newsnow_neon.application`, while the concrete implementations still live in `legacy_app.py`.
   - This reduces one hidden dependency, but the overall runtime boundary is not fully separated yet.

3. **There are still false or dead package surfaces**
   - `newsnow_neon/app/services.py` still collides with `newsnow_neon/app/services/`, but explicit file-path loads now re-export the canonical stable package proxies.
   - `newsnow_neon/app/controller.py` still exists beside `newsnow_neon/app/controller/`, but it is now only a compatibility alias instead of a second class surface.
   - The remaining cleanup question is whether these parallel shapes should keep existing at all.

4. **Back-compat contract is retained and service dispatch is proven**
   - Stage 3C confirmed that normal imports resolve to the controller package,
     while `app/controller.py` is an identity-preserving compatibility file with
     no internal normal-import consumer.
   - The P0 owner decision retains file-path and historical direct-submodule
     compatibility as supported external interfaces.
   - `controller.py` has an identity regression test; P1 made `services.py`
     re-export canonical package proxies and added a file-path dispatch
     regression test after configuration.

5. **Core product behavior has bounded offline coverage; end-to-end coverage remains incomplete**
   - Current tests cover startup/bootstrap/diagnostics plus fixture or mock-based:
     - NewsNow parsing,
     - settings persistence normalization,
     - cache/history payload behavior,
     - summary/provider fallback.
   - Current tests do not yet prove live NewsNow availability, live provider
     behavior, Redis deployment compatibility, or main GUI/controller workflows.

6. **Static quality debt is measured, not hidden**
   - Ruff baseline: 942 diagnostics on the current repository-wide scope.
   - Pyright baseline: 536 errors and 15 warnings on the current repository-wide scope.
   - These are not blocking CI until reduced through bounded slices.

7. **Version truth is not yet unified**
   - `pyproject.toml`, runtime metadata, and per-file update annotations are not yet obviously one coherent release truth.

### Do weryfikacji

- whether `--check` should fail hard on missing required launch prerequisites in v1,
- whether Redis/LLM optional state belongs in the main diagnostics output now or later,
- how much of the package-surface collision problem is safe to remove without breaking compatibility,
- whether the controller compatibility exports are used anywhere external,
- how much real GUI smoke should be added once a display-capable environment is available.

## North star

Make NewsNowNeon feel like a **trustworthy desktop monitoring tool** rather than a useful but fragile prototype.

That means:
- startup failures are classified clearly,
- runtime expectations are explicit,
- docs match reality,
- environment issues are separable from app regressions,
- package structure does not pretend to be more modular than it really is,
- core operator workflows are covered enough to refactor safely.

## Updated roadmap order

### Priority 1 — make the legacy boundary explicit

Goal:
Stop relying on unclear import side effects to construct a valid runtime.

This includes:
- documenting the exact role of `legacy_app.py`,
- making service wiring explicit,
- proving the supported app-construction path with focused tests,
- reducing the risk of bypassing setup accidentally.

Success condition:
The supported app startup path is explicit, testable, and does not depend on hidden import magic.

### Priority 2 — remove false package architecture surfaces

Goal:
Remove or reconcile package/file shapes that suggest architecture which is not actually active at runtime.

This includes:
- resolving `services.py` vs `services/`,
- resolving `controller.py` vs `controller/`,
- deleting or fixing dead scaffolds,
- keeping compatibility only where it is real and useful.

Success condition:
The package layout reflects the actual runtime architecture and does not mislead contributors.

### Priority 3 — typed and explicit UI/controller seams

Goal:
Reduce ambiguous dynamic-Tk coupling by introducing clearer contracts where the modular UI/controller layer leaks state.

This includes:
- picking one active seam,
- introducing the smallest useful `Protocol` or runtime contract,
- improving Pyright signal locally without pretending the repo is globally strict-clean.

Success condition:
One active seam becomes cleaner, typed enough to be useful, and cheaper to modify safely.

### Priority 4 — preserve bounded product-behavior coverage

Goal:
Keep the completed fixture/mock coverage trustworthy while adding a live or GUI
acceptance check only when its environment and provider scope are explicitly
approved.

This includes:
- preserving parsing, settings, cache/history, and summary-fallback regression tests,
- adding one bounded GUI/controller or live integration check only with an
  explicit acceptance contract,
- keeping offline behavior tests separate from claims about deployed services.

Success condition:
Core behavior remains protected locally, and any live acceptance evidence is
clearly scoped and reproducible.

### Priority 5 — broader quality recovery after boundaries are real

Goal:
Only after runtime/readiness, legacy boundary, false package surfaces, and one typed seam are clarified, decide how to recover broader Ruff/Mypy signal.

This includes:
- deciding quality boundaries intentionally,
- limiting strictness to trustworthy seams first,
- avoiding repo-wide cleanup that outruns architecture truth.

Success condition:
Quality gates become meaningful instead of aspirational noise.

## Ordered implementation backlog

1. **Legacy service-boundary slice**
   - Make service wiring explicit instead of relying on `legacy_app` import side effects.
   - Add one import-order / construction-path test.
   - Document the runtime role of `legacy_app.py`.

2. **Package-surface cleanup slice**
   - Continue from the lazy controller-package export change, the new real `app.services` package surface, and the controller-file compatibility alias cleanup.
   - Resolve `services.py` vs `services/`.
   - Resolve `controller.py` vs `controller/`.
   - Fix or remove non-working compatibility exports.

3. **Single typed seam slice**
   - Pick one active controller/UI seam.
   - Add the smallest useful protocol/runtime contract.
   - Scope Pyright to that seam and supporting files.

4. **Core product regression-maintenance slice**
   - Preserve fixture/mock coverage for parsing, settings, cache/history, and
     summary fallback.
   - Add a GUI/controller or live integration case only through an explicit,
     separately approved acceptance scope.

5. **Version-truth cleanup slice**
   - Choose one clear source of release/version truth.
   - Align runtime metadata, package version, changelog, and per-file update annotations.

## Current recommended next slice

### Active next slice
**Stage 4R — native color-chooser cancel-path acceptance**

### Why this is next
- Stage 4Q repaired and verified the settings-store round-trip for custom colors
  on both real ticker bands.
- The GUI primary surface still has one bounded interaction not exercised:
  opening and cancelling the native color chooser through its actual buttons.
- A cancel-only path tests dialog reachability and no-op safety without selecting
  colors, touching user settings, or extending this into native-dialog E2E.

## Implementation focus for the active next slice

### Goal
Open and cancel each real native color chooser against a controlled temporary
settings store, verifying that cancellation leaves the appearance state and
persisted values unchanged.

### Scope
The next slice should:
- start the real Tk app with offline service doubles and temporary settings;
- open `Background…` and `Text…` through their normal UI actions;
- capture the real dialog reachability where the desktop supports it, then
  cancel rather than select a value;
- verify both ticker colors and the temporary store are unchanged afterward.

### Non-goals
Do not in this slice:
- choose a color, confirm a color dialog, or alter user settings,
- call NewsNow, a provider, or Redis for acceptance evidence,
- claim native dialog behavior where the host desktop cannot expose it,
- redesign the color controls or alter public imports.

### Preferred execution order
1. inspect the native dialog behavior and available desktop automation boundary
2. run the controlled open/cancel attempt for each button
3. compare in-memory and persisted appearance values before and after cancellation
4. classify unsupported desktop automation honestly rather than simulating a
   native dialog in a stub

### Acceptance criteria
- each chooser is either visibly opened then cancelled with no state change, or
  explicitly reported as unsupported by the desktop boundary
- temporary-store values and both ticker colors remain unchanged after cancel
- no user setting, live service, or selected color is involved
- the report distinguishes real dialog evidence from any unsupported path

## What should not drive the roadmap now

Do not prioritize these before the readiness-contract slice:
- repo-wide Ruff cleanup,
- repo-wide Mypy cleanup,
- broad UI redesign or framework replacement; bounded GUI runtime and visual
  acceptance work is in scope because the desktop workflow is primary,
- deep legacy refactors without a bounded seam,
- feature expansion unrelated to operator trust.

## Engineering rules for this repo

- Prefer bounded slices over wide rewrites.
- Keep `pytest` green after every slice.
- Verify runtime claims with real command output before documenting them as shipped.
- Separate explicitly:
  - **potwierdzone** — confirmed by code/tests/tool output,
  - **do weryfikacji** — needs confirmation in another runtime or on another machine.
- Prefer simple local fixes over new abstraction layers.
- Sync docs when user-visible operational behavior changes.
- Do not let package structure claim boundaries that runtime behavior does not really support.

## Documentation sync rules

The following files must stay aligned with this SSOT:
- `PLAN.md`
- `BOUNDS.md`
- `AGENTS.md`
- `README.md`
- `README-DEV.md`
- `CHANGELOG.md`

Current sync status:
- root `PLAN.md`, `BOUNDS.md`, and `AGENTS.md` define the current delivery,
  execution, and agent contracts
- README links the root contracts and this canonical SSOT
- CHANGELOG records the operational contract refresh

## Status summary

### Potwierdzone
- the repo has a working hardened startup contract for the main front doors
- `--check` exists on supported front doors, avoids GUI launch, and now returns a readiness verdict with non-zero exit for failed required prerequisites
- full local `pytest -q` is green
- missing Tk and missing display now surface as bounded CLI-facing outcomes instead of raw startup tracebacks
- fixture/mock coverage now protects parsing, settings, cache/history, and summary-provider fallback seams
- Stage 4A reduced the `app/actions.py` Ruff seam from 3 diagnostics to 0 and
  added focused mute-action regression coverage
- Stage 4B reduced the `app/filtering.py` Ruff seam from 12 diagnostics to 0 and
  added focused filtering regression coverage
- Stage 4C reduced the `app/rendering.py` Ruff seam from 16 diagnostics to 0 and
  added focused rendering regression coverage
- Stage 4D reduced the `app/helpers/env_helpers.py` Ruff seam from 3 diagnostics
  to 0 and added focused environment-logging regression coverage
- Stage 4E reduced the `app/services/news_service.py` Ruff seam from 7 diagnostics
  to 0 and added focused unconfigured-provider regression coverage
- Stage 4F reduced the `app/services/cache_service.py` Ruff seam from 2 diagnostics
  to 0 and added focused unconfigured-provider regression coverage
- Stage 4G reduced the `app/controller/refresh_controller.py` Ruff seam from 2
  diagnostics to 0 and added focused refresh-controller regression coverage
- Stage 4H reduced the `app/controller/auto_refresh_controller.py` Ruff seam
  from 1 diagnostic to 0 and added focused pending-job cancellation coverage
- Stage 4I removed 57 redundant top-level helper definitions from
  `legacy_app.py`, retaining the final active implementations; an AST
  structural regression test and offline helper-contract coverage protect the
  consolidation. The repository-wide baselines are now Ruff `968` diagnostics
  and Pyright `536` errors plus `15` warnings.
- Stage 4J reduced the `app/controller/background_watch_controller.py` Ruff
  seam from 16 diagnostics to 0 without runtime behavior changes. Existing
  focused background-watch/settings coverage remained green and scoped
  Pyright stayed at 0 errors and 0 warnings. The repository-wide baselines are
  now Ruff `952` diagnostics and Pyright `536` errors plus `15` warnings.
- Stage 4K reduced the `app/controller/highlight_controller.py` Ruff seam from
  10 diagnostics to 0 without runtime behavior changes. Existing focused
  highlight/settings coverage remained green and scoped Pyright stayed at 0
  errors and 0 warnings. The repository-wide baselines are now Ruff `942`
  diagnostics and Pyright `536` errors plus `15` warnings.
- Stage 4L added `tests/test_gui_runtime_smoke.py`: an isolated real-Tk
  subprocess smoke that renders one offline headline through the application
  event loop and verifies the main list/ticker. It does not call NewsNow,
  Redis, or provider services.
- Stage 4M visually confirmed an offline `900×450` X11 window, the primary
  list/ticker, and the full Controls-toggle cycle. It is partial because the
  options-panel group headings were outside the visible controls area.
- Stage 4N moved the existing options panel before history, making both group
  headings visible in real Tk at `900×450`; the smoke also protects the full
  toggle cycle and close-state headline rows.
- Stage 4O compacted only existing appearance-panel vertical spacing, restoring
  both color buttons to their full requested height at `900×450` without overlap.
- Stage 4P classified observed ticker edge clipping as normal marquee motion by
  controlled real-Tk coordinates and paired X11 captures; no ticker change made.
- Stage 4Q repaired custom-color persistence across a fresh Tk restart for both
  ticker bands; a controlled X11 capture confirmed the restored rendering.
- the next bounded task is Stage 4R native color-chooser cancel-path acceptance

### Do weryfikacji
- whether Redis/LLM optional reporting belongs in a future extension of the readiness contract
- exact compatibility impact of package-surface cleanup
- GUI-specific smoke beyond current command-line/runtime checks
