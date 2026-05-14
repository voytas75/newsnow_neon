# NewsNowNeon Product SSOT

Status: active  
Canonical file: `docs/product-ssot.md`  
Updated: 2026-05-14

## Purpose

This document is the single source of truth for NewsNowNeon product direction, operational hardening priorities, and quality-improvement order.

It consolidates what the current repo already says in:
- `README.md`
- `README-DEV.md`
- `AGENTS.md`
- `pyproject.toml`

When those files drift, this file wins and the others should be synced to it.

## Product definition

NewsNowNeon is a desktop news dashboard for curated NewsNow headlines with:
- headline aggregation,
- scrolling ticker + list views,
- cached article summaries,
- persistent operator settings,
- optional Redis-backed history and diagnostics.

It is not:
- a generic LLM workstation,
- a workflow orchestrator,
- a broad automation platform,
- a backend service-first product.

Primary product center:
- **fast headline monitoring and triage in a desktop UI**.

Supporting layers:
- **operational reliability** — predictable startup, usable diagnostics, stable refresh/caching behavior.
- **engineering quality** — maintainable module boundaries, runnable checks, and safe incremental refactoring.

## Confirmed current baseline

Confirmed from repo state on 2026-05-14:
- package: `newsnow-neon`
- version in `pyproject.toml`: `0.53.0`
- runtime model: Tkinter desktop app with package entrypoint files present
- tests: `pytest -q` passing (`19 passed` in the review snapshot)
- static quality baseline is weak:
  - `ruff check .` reports high error volume
  - `mypy newsnow_neon` reports high error volume
- local GUI runtime was not confirmed in the Hermes environment because `tkinter` is missing there

Interpretation:
- the project has a working codebase and passing focused tests,
- but is not yet operationally polished or quality-stable enough to treat as fully hardened.

## North star

Make NewsNowNeon feel like a **reliable desktop operator tool** rather than a useful prototype.

That means:
- startup is predictable,
- runtime expectations are explicit,
- docs match reality,
- quality checks are scoped and trustworthy,
- modular code can be improved without reopening the whole legacy surface every time.

## Roadmap order

### Priority 1 — operational readiness and truthful runtime contract

Goal:
Make the app easy to start, understand, and verify on a real desktop machine.

This includes:
- confirming and documenting the real entrypoint contract,
- documenting platform requirements explicitly, especially `tkinter`,
- aligning README and developer docs with real startup behavior,
- adding a bounded smoke-verification path for launch/bootstrap,
- separating environment failures from application failures.

Success condition:
A developer can read the docs, install the known prerequisites, and understand exactly how to launch and verify the app.

### Priority 2 — quality-noise reduction on the non-legacy front door

Goal:
Reduce obvious engineering noise in the entrypoint and shared support surfaces before attacking the legacy core.

This includes:
- cleanup of front-door files such as `__main__.py`, `main.py`, `utils.py`, and selected small UI windows,
- import/order/docstring/type-modernization cleanup,
- reducing low-value Ruff noise in small safe slices,
- keeping tests green after each slice.

Success condition:
The front door and small support modules become clean enough that future work is less noisy and less risky.

### Priority 3 — typed and explicit UI/controller seams

Goal:
Stop the modularized Tkinter layer from generating large amounts of ambiguous static-analysis noise.

This includes:
- deciding the intended typing boundary for the app/controller/UI surface,
- introducing explicit app-state contracts or limited typing boundaries where justified,
- reducing repeated `Tk has no attribute ...` errors by design rather than by ad hoc suppression,
- keeping the solution simple and local-first.

Success condition:
The modular UI/controller layer has a clear contract and static analysis becomes more meaningful.

### Priority 4 — legacy boundary containment

Goal:
Treat `legacy_app.py` as a deliberate compatibility boundary instead of a constantly leaking maintenance burden.

This includes:
- documenting its role explicitly,
- reducing accidental coupling between new modules and legacy internals,
- deciding which checks apply strictly outside the legacy boundary,
- moving future work into modular files instead of reopening the monolith by default.

Success condition:
New work can continue safely without pretending the entire legacy surface must be fully cleaned at once.

### Priority 5 — deeper UX polish after operational trust is restored

Goal:
Only after priorities 1–4 improve trust, continue UI/feature polish.

This includes:
- clarity of diagnostics/status labels,
- smoother refresh/history/Redis operator flows,
- higher-confidence summary and cache surfaces,
- bounded UX improvements driven by observed friction.

Success condition:
Polish work is built on a trustworthy runtime and maintainable code path, not on top of unresolved foundation issues.

## Ordered implementation backlog

1. **Runtime contract and docs sync**
   - Create canonical SSOT and sync repo-facing docs to it.
   - Add explicit startup prerequisites and known platform requirements.
   - Clarify the supported launch command and verification path.

2. **Smoke verification slice**
   - Add a bounded non-interactive startup/bootstrap verification path where possible.
   - Ensure docs distinguish missing OS GUI deps from app regressions.

3. **Front-door hygiene slice**
   - Clean `newsnow_neon/__main__.py`, `newsnow_neon/main.py`, `newsnow_neon/utils.py`.
   - Remove trivial Ruff noise in those files.
   - Keep behavior unchanged.

4. **Small-window cleanup slice**
   - Clean one or two isolated UI window modules first (`app_info_window.py`, `redis_stats_window.py`, `summary_window.py` are likely candidates).
   - Prefer local cleanup with tests over wide refactors.

5. **UI/controller contract slice**
   - Define how the modular Tkinter surface should be typed.
   - Introduce the smallest explicit boundary that reduces repeated attribute errors.

6. **Legacy containment slice**
   - Mark and constrain `legacy_app.py` as a compatibility boundary.
   - Adjust check expectations and developer docs accordingly.

7. **Broader quality recovery plan**
   - After the seams above are cleaner, decide whether Ruff/Mypy debt should be reduced by package, by feature seam, or by boundary configuration.

## What should not drive the roadmap

Do not prioritize these before the foundation work above:
- broad new feature expansion,
- UI redesign for its own sake,
- large architectural rewrites,
- replacing Tkinter only because tooling around it is noisy,
- repo-wide style cleanups without a bounded seam,
- trying to eliminate all legacy debt in one pass.

## Engineering rules for this repo

- Prefer bounded slices over wide rewrites.
- Keep `pytest` green after every slice.
- Verify real runtime claims before documenting them as done.
- Separate:
  - **potwierdzone** — confirmed by code/tests/tool output,
  - **do weryfikacji** — needs real desktop/runtime confirmation.
- Prefer simple, local fixes over framework-heavy abstractions.
- Improve docs and code together when changing operational behavior.

## Documentation sync rules

The following files must stay aligned with this SSOT:
- `README.md` — user-facing installation, startup, feature framing
- `README-DEV.md` — developer setup, environment, workflow, architecture notes
- `CHANGELOG.md` — shipped history once created/populated

Current doc gaps to close:
- `docs/` directory did not exist before this SSOT was created
- `CHANGELOG.md` has now been added and should stay aligned with shipped slices
- README/README-DEV should be updated to reflect this SSOT and current operational priorities

## Current execution recommendation

Recommended first execution slice:
- **entrypoint + runtime prerequisites + README/README-DEV sync**

Reason:
- it improves operator trust immediately,
- it is lower risk than attacking the Tkinter typing debt first,
- it creates a stable base for later quality work.

## Status summary

### Potwierdzone
- repo has passing focused tests
- repo has substantial static-analysis debt
- desktop runtime is not confirmed in the current Hermes environment
- current highest-value improvement area is operational polish plus bounded quality hardening

### Do weryfikacji
- exact supported startup path on a machine with working `tkinter`
- whether `python -m newsnow_neon` is the final supported invocation in the intended user environment
- how far current docs differ from real runtime behavior on the user’s actual desktop
