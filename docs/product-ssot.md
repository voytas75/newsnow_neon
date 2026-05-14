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
- subprocess smoke coverage exists for:
  - module front door without `tkinter`
  - `__main__` / console-script path without `tkinter`
- static-quality debt remains high at repo scope and is not yet the active primary slice

Interpretation:
- the app now has a materially more trustworthy startup/runtime contract,
- but broader maintainability and legacy-boundary work still remain.

## North star

Make NewsNowNeon feel like a **trustworthy desktop monitoring tool** rather than a useful but fragile prototype.

That means:
- startup failures are classified clearly,
- runtime expectations are explicit,
- docs match reality,
- environment issues are separable from app regressions,
- future quality work lands in bounded slices instead of reopening the whole legacy surface.

## Roadmap order

### Priority 1 — operational trust and diagnostics-first runtime contract

Goal:
Make the app easy to verify before and during launch on a real desktop machine.

This includes:
- preserving the hardened startup contract,
- adding an explicit non-GUI diagnostics path,
- checking Tk/display/settings/runtime prerequisites without requiring full app launch,
- making operator-visible failure states short and actionable,
- keeping docs aligned with real runtime behavior.

Success condition:
A developer or operator can run one clear diagnostic path and know whether the environment is launch-ready before troubleshooting the GUI itself.

### Priority 2 — bounded front-door and support-surface cleanup

Goal:
Reduce engineering noise around entrypoints and small support modules without widening into a repo-wide cleanup.

This includes:
- front-door cleanup in `__main__.py`, `main.py`, `utils.py`, and other small support seams,
- bounded cleanup of small windows/helpers,
- preserving behavior while tightening lint/type signal in touched seams.

Success condition:
Front-door and adjacent support modules remain low-risk, readable, and cheap to modify.

### Priority 3 — typed and explicit UI/controller seams

Goal:
Reduce ambiguous dynamic-Tk coupling by introducing clearer contracts where the modular UI/controller layer currently leaks state.

This includes:
- defining the intended typing boundary for app/controller/UI seams,
- reducing repeated `Tk has no attribute ...` style debt by design,
- keeping the solution local and minimal.

Success condition:
Static analysis on active non-legacy seams becomes more meaningful and less noisy.

### Priority 4 — legacy boundary containment

Goal:
Treat `legacy_app.py` as a deliberate compatibility boundary instead of a constantly expanding maintenance surface.

This includes:
- documenting its role explicitly,
- reducing accidental coupling to new code,
- moving future work into modular files by default,
- deciding which checks stay strict outside the legacy boundary.

Success condition:
New work can continue safely without pretending the whole monolith must be cleaned in one pass.

### Priority 5 — deeper UX polish after trust is restored

Goal:
Only after operational trust and maintainability improve, continue UI/feature polish.

This includes:
- better status/diagnostic cues,
- smoother refresh/history/Redis operator flows,
- clearer cache/summary surfaces,
- bounded polish driven by observed operator friction.

Success condition:
Polish work sits on top of a trustworthy runtime and cleaner seams.

## Ordered implementation backlog

1. **Diagnostics command / startup readiness check**
   - Add a non-GUI diagnostics command such as `newsnow-neon --check`.
   - Verify Python/Tk/display/settings-path readiness before full GUI launch.
   - Keep output short, terminal-friendly, and explicitly split into confirmed vs failing prerequisites.

2. **Diagnostics docs sync**
   - Document the check flow in `README.md` and `README-DEV.md`.
   - Clarify how to interpret environment failures vs app regressions.

3. **Front-door/support cleanup continuation**
   - Continue bounded cleanup in small non-legacy files only.
   - Keep tests green and avoid scope expansion.

4. **UI/controller contract slice**
   - Pick one active seam and define the smallest explicit runtime contract.

5. **Legacy containment slice**
   - Mark and constrain `legacy_app.py` as a compatibility boundary with explicit expectations.

6. **Broader quality recovery decision**
   - Only after the above, decide how Ruff/Mypy debt should be reduced by seam/boundary.

## Current recommended next slice

### Active next slice
**Diagnostics command / `--check`**

### Why this is next
- It builds directly on the now-hardened startup contract.
- It improves operator trust without requiring GUI launch.
- It gives a reusable troubleshooting path for missing Tk, missing display, and bad local runtime setup.
- It is smaller and safer than jumping straight into legacy containment or broad typing work.

## Implementation plan for the next slice

### Goal
Add a terminal-first diagnostics path that verifies launch readiness without starting the GUI.

### Scope
The diagnostics command should report, at minimum:
- Python version
- package/app version
- whether `tkinter` is importable
- whether a GUI display looks available in the current environment
- whether the settings path can be resolved and is writable
- optional note when Redis/LLM-related env is absent, but without turning optional integrations into hard failures

### Non-goals
Do not in this slice:
- build a TUI,
- add deep Redis live probing unless it is already trivial and low-risk,
- redesign the startup contract,
- widen into global refactors.

### Preferred UX
- one clear command, ideally through the existing front door / console script surface,
- short output,
- explicit separation between:
  - **potwierdzone**,
  - **problem / missing prerequisite**,
  - **optional / not configured**.

### Suggested execution order
1. inspect current CLI/front-door seams and choose the smallest place to add `--check`
2. write failing behavior tests for the diagnostics mode
3. implement the minimal command path without disturbing normal GUI launch
4. run focused tests
5. run real CLI smoke for `--check`
6. sync README / README-DEV / CHANGELOG if shipped behavior changes visibly

### Acceptance criteria
- `newsnow-neon --check` or equivalent supported diagnostics invocation exists
- it does not start the GUI mainloop
- it returns useful terminal output for:
  - Tk missing
  - display missing
  - settings path readiness
- normal launch flow still works unchanged
- tests cover the diagnostics path

## What should not drive the roadmap now

Do not prioritize these before the diagnostics slice:
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

## Documentation sync rules

The following files must stay aligned with this SSOT:
- `README.md`
- `README-DEV.md`
- `CHANGELOG.md`

Current sync status:
- README and README-DEV already point to this canonical SSOT
- CHANGELOG reflects the recent startup-hardening slice
- next sync point should happen when the diagnostics command ships

## Status summary

### Potwierdzone
- the repo has a working hardened startup contract for the main front doors
- full local `pytest -q` is green
- missing Tk and missing display now surface as bounded CLI-facing outcomes instead of raw startup tracebacks
- the next highest-value slice is diagnostics-first runtime verification

### Do weryfikacji
- final exact diagnostics invocation shape (`--check` on which front door surface)
- whether Redis/LLM optional status belongs in v1 diagnostics output or a later follow-up
- any GUI-specific smoke beyond current command-line/runtime checks
