# NewsNowNeon Product SSOT

Status: active  
Canonical file: `docs/product-ssot.md`  
Updated: 2026-05-14

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
- static-quality debt remains high at repo scope and is not yet the active primary slice

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

2. **Legacy boundary is still implicit**
   - `load_app_class()` imports `newsnow_neon.legacy_app`, but the app class itself comes from `newsnow_neon.application`.
   - `legacy_app` still matters because service configuration depends on import side effects.
   - This means the runtime boundary is real but not explicit.

3. **There are false or dead package surfaces**
   - `newsnow_neon/app/services.py` collides with `newsnow_neon/app/services/`.
   - `newsnow_neon/app/controller.py` collides with `newsnow_neon/app/controller/`.
   - Some files look like active architecture but are not the effective runtime path.

4. **Back-compat exports are not trustworthy yet**
   - The compatibility export for `AINewsApp` in the controller package is not a reliable public surface.
   - This is small in scope, but it signals that some package boundaries claim more stability than they currently provide.

5. **Core product behavior is still weakly covered**
   - Current tests strongly cover startup/bootstrap/diagnostics seams.
   - Current tests do not yet strongly cover:
     - scraping/parsing,
     - settings persistence,
     - cache/history behavior,
     - summary/provider fallback,
     - main UI/controller workflows.

6. **Version truth is not yet unified**
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
- improving mypy signal locally without pretending the repo is globally strict-clean.

Success condition:
One active seam becomes cleaner, typed enough to be useful, and cheaper to modify safely.

### Priority 4 — core product behavior smoke coverage

Goal:
Extend test confidence beyond startup and into the actual operator workflow.

This includes:
- scraping/parsing tests with fixtures,
- settings persistence tests,
- cache/history tests,
- summary/provider fallback tests,
- bounded workflow tests around main operator flows.

Success condition:
The repo can protect core product behavior, not only front-door behavior.

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
   - Resolve `services.py` vs `services/`.
   - Resolve `controller.py` vs `controller/`.
   - Fix or remove non-working compatibility exports.

3. **Single typed seam slice**
   - Pick one active controller/UI seam.
   - Add the smallest useful protocol/runtime contract.
   - Scope mypy to that seam and supporting files.

4. **Core product smoke slice**
   - Add tests for scraping/parsing.
   - Add tests for settings persistence.
   - Add tests for cache/history/summary fallback behavior.

5. **Version-truth cleanup slice**
   - Choose one clear source of release/version truth.
   - Align runtime metadata, package version, changelog, and per-file update annotations.

## Current recommended next slice

### Active next slice
**Legacy service-boundary slice**

### Why this is next
- The readiness contract is now shipped for `--check`.
- The biggest remaining operational risk is still implicit service wiring through `legacy_app` import side effects.
- This slice is smaller and safer than jumping straight into package-surface cleanup or typed UI work.
- It reduces the chance of future refactors bypassing required runtime setup.

## Implementation focus for the active next slice

### Goal
Make the supported app-construction path explicit and testable.

### Scope
The next slice should:
- identify exactly what `legacy_app.py` still provides at startup,
- make service wiring explicit where feasible,
- prove the supported construction/import path with focused tests,
- keep public launch behavior unchanged.

### Non-goals
Do not in this slice:
- broadly refactor `legacy_app.py`,
- solve all package-layout collisions,
- widen into repo-wide cleanup,
- redesign the UI/controller layer.

### Preferred execution order
1. inspect current service wiring and import side effects
2. write a focused failing test for the supported construction path
3. make the smallest explicit wiring change
4. verify startup tests and real smoke still pass
5. sync docs/changelog only if the runtime story changes visibly

### Acceptance criteria
- the supported app startup path is documented by code/tests rather than import magic alone
- service wiring is less dependent on hidden side effects
- startup/readiness behavior remains unchanged for users
- focused tests cover the supported path

## What should not drive the roadmap now

Do not prioritize these before the readiness-contract slice:
- repo-wide Ruff cleanup,
- repo-wide Mypy cleanup,
- framework replacement,
- broad UI redesign,
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
- `README.md`
- `README-DEV.md`
- `CHANGELOG.md`

Current sync status:
- README and README-DEV point to this canonical SSOT
- CHANGELOG reflects startup hardening, diagnostics shipping, and readiness-contract semantics for `--check`
- next sync point should happen when the legacy service-boundary slice changes the supported startup-construction story

## Status summary

### Potwierdzone
- the repo has a working hardened startup contract for the main front doors
- `--check` exists on supported front doors, avoids GUI launch, and now returns a readiness verdict with non-zero exit for failed required prerequisites
- full local `pytest -q` is green
- missing Tk and missing display now surface as bounded CLI-facing outcomes instead of raw startup tracebacks
- the next highest-value slice is making the legacy service boundary explicit
- review surfaced real package-boundary and legacy-boundary gaps, not just cosmetic cleanup ideas

### Do weryfikacji
- whether Redis/LLM optional reporting belongs in a future extension of the readiness contract
- exact compatibility impact of package-surface cleanup
- GUI-specific smoke beyond current command-line/runtime checks
