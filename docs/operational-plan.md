# NewsNow Neon — Operational Plan

**Status:** active — Stage 12 Redis Stats real-Tk acceptance verified locally with controlled offline evidence; Stage 1 and Stage 2 verified remotely; governance controls refreshed in this slice.
**Updated:** 2026-08-09
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

**Status:** completed locally; the retained code is covered by later successful
main CI run [#31326233486](https://github.com/voytas75/newsnow_neon/actions/runs/31326233486).

**Changed:** `app/services/__init__.py` now retains stable public proxies and
updates private implementation slots during configuration. Direct imports taken
before startup configuration therefore dispatch correctly afterward.

**Validation:** focused bootstrap/service tests, full frozen pytest, scoped
Ruff, scoped Pyright, and Python compilation all passed. Evidence is in
[`service-proxy-binding.md`](service-proxy-binding.md).

**Next:** Stage 4A is the first bounded static-debt reduction seam following
the completed Stage 3C inventory and P0/P1 compatibility decisions.

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

## Stage 4A — mute-action static seam

**Status:** completed locally at `2af3de2`.

**Scope:** `newsnow_neon/app/actions.py` and its focused regression module
`tests/test_actions.py`.

**Changed:** replaced two legacy `Optional[str]` annotations with `str | None`,
removed one redundant blank line, and added four tests covering mute-keyword
and source-term behavior. No runtime behavior changed.

**Measured result:** scoped Ruff diagnostics `3 → 0`; scoped Pyright remained
`0 errors, 0 warnings`. The full pytest suite passed. The fresh repository-wide
baseline is Ruff `1,134` diagnostics and Pyright `641` errors plus `15` warnings;
global Pyright remains intentionally non-blocking.

**Next:** select one new behavior-owned seam for Stage 4B.

## Stage 4B — filtering static seam

**Status:** completed locally at `f7b6fa8`.

**Scope:** `newsnow_neon/app/filtering.py` and its focused regression module
`tests/test_filtering.py`.

**Changed:** migrated legacy `typing` collection annotations to modern built-in
and `collections.abc` forms, with no runtime behavior change. Added three tests
covering case-insensitive filtering, ordered exclusion normalization, and
unsupported persisted values.

**Measured result:** scoped Ruff diagnostics `12 → 0`; scoped Pyright remained
`0 errors, 0 warnings`. The full pytest suite passed. The fresh repository-wide
baseline is Ruff `1,122` diagnostics and Pyright `641` errors plus `15` warnings;
global Pyright remains intentionally non-blocking.

**Next:** select one new behavior-owned seam for Stage 4C.

## Stage 4C — rendering static seam

**Status:** completed locally at `cc59984`.

**Scope:** `newsnow_neon/app/rendering.py` and its focused regression module
`tests/test_rendering.py`.

**Changed:** migrated legacy collection/optional annotations to modern forms,
with no runtime behavior change. Added three tests covering deterministic age
bucket ordering, relative-age boundaries, and metadata fallbacks.

**Measured result:** scoped Ruff diagnostics `16 → 0`; scoped Pyright remained
`0 errors, 0 warnings`. The full pytest suite passed. The fresh repository-wide
baseline is Ruff `1,106` diagnostics and Pyright `641` errors plus `15` warnings;
global Pyright remains intentionally non-blocking.

**Next:** select one new behavior-owned seam for Stage 4D.

## Stage 4D — environment logging static seam

**Status:** completed locally at `f125cfb`.

**Scope:** `newsnow_neon/app/helpers/env_helpers.py` and its focused regression
module `tests/test_env_helpers.py`.

**Changed:** migrated a legacy optional annotation and completed the Returns
docstring spacing, with no runtime behavior change. Added three tests covering
sensitive-value masking, ordinary/long value handling, and empty-value omission.

**Measured result:** scoped Ruff diagnostics `3 → 0`; scoped Pyright remained
`0 errors, 0 warnings`. The full pytest suite passed. The fresh repository-wide
baseline is Ruff `1,103` diagnostics and Pyright `641` errors plus `15` warnings;
global Pyright remains intentionally non-blocking.

**Next:** select one new behavior-owned seam for Stage 4E.

## Stage 4E — news-service static seam

**Status:** completed locally at `6690d33`.

**Scope:** `newsnow_neon/app/services/news_service.py` and its focused
regression module `tests/test_news_service.py`.

**Changed:** migrated legacy provider annotations to modern collection and
optional forms, with no runtime behavior change. Added one focused contract test
that every unconfigured stub raises the existing actionable configuration error.

**Measured result:** scoped Ruff diagnostics `7 → 0`; scoped Pyright remained
`0 errors, 0 warnings`. The full pytest suite passed. The fresh repository-wide
baseline is Ruff `1,096` diagnostics and Pyright `641` errors plus `15` warnings;
global Pyright remains intentionally non-blocking.

**Next:** select one new behavior-owned seam for Stage 4F.

## Stage 4F — cache-service static seam

**Status:** completed locally at `8ec3e70`.

**Scope:** `newsnow_neon/app/services/cache_service.py` and its focused
regression module `tests/test_cache_service.py`.

**Changed:** migrated the legacy tuple annotation to its modern built-in form,
with no runtime behavior change. Added one focused contract test that the
unconfigured cache stub raises the existing actionable configuration error.

**Measured result:** scoped Ruff diagnostics `2 → 0`; scoped Pyright remained
`0 errors, 0 warnings`. The full pytest suite passed. The fresh repository-wide
baseline is Ruff `1,094` diagnostics and Pyright `641` errors plus `15` warnings;
global Pyright remains intentionally non-blocking.

**Next:** select one new behavior-owned seam for Stage 4G.

## Stage 4G — refresh-controller static seam

**Status:** completed locally at `4278ac8`.

**Scope:** `newsnow_neon/app/controller/refresh_controller.py` and its focused
regression module `tests/test_refresh_controller.py`.

**Changed:** removed an unused typing import and documented the controller
initialization, with no runtime behavior change. Added one focused test covering
history exit, status update, and daemon worker launch for manual refresh.

**Measured result:** scoped Ruff diagnostics `2 → 0`; scoped Pyright remained
`0 errors, 0 warnings`. The full pytest suite passed. The fresh repository-wide
baseline is Ruff `1,092` diagnostics and Pyright `641` errors plus `15` warnings;
global Pyright remains intentionally non-blocking.

**Next:** select one new behavior-owned seam for Stage 4H.

## Stage 4H — auto-refresh-controller static seam

**Status:** completed locally at `623bac6`.

**Scope:** `newsnow_neon/app/controller/auto_refresh_controller.py` and its
focused regression module `tests/test_auto_refresh_controller.py`.

**Changed:** documented the controller initialization, with no runtime behavior
change. Added two focused tests covering successful cancellation of both pending
jobs and safe identifier clearing when Tk cancellation reports an expired job.

**Measured result:** scoped Ruff diagnostics `1 → 0`; scoped Pyright remained
`0 errors, 0 warnings`. The full pytest suite passed. The fresh repository-wide
baseline is Ruff `1,091` diagnostics and Pyright `641` errors plus `15` warnings;
global Pyright remains intentionally non-blocking.

**Next:** select one new behavior-owned seam for Stage 4J.

## Stage 4I — legacy duplicate-helper consolidation

**Status:** completed locally.

**Scope:** `newsnow_neon/legacy_app.py` and
`tests/test_legacy_helper_consolidation.py`.

**RED:** the new AST structural regression test established that three private
helper names had 25, 25, and 10 top-level definitions respectively.

**Changed:** removed the continuous duplicate block at lines 435–2771 from the
pre-change file: 57 redundant definitions plus their adjacent blank lines. The
final active definitions of `_normalize_href`, `_resolve_final_url`, and
`_extract_completion_text` remain. The new offline test protects both singular
definition counts and retained helper behavior without network, provider, Redis,
or GUI access.

**Validation:** focused helper/parsing/summary tests passed; the full frozen
pytest suite passed; the new test is Ruff- and Pyright-clean; and
`py_compile newsnow_neon/legacy_app.py` passed.

**Measured result:** repository-wide Ruff fell from `1,091` to `968`
diagnostics and Pyright from `641` to `536` errors (warnings remain `15`).
Both repository-wide checks intentionally remain non-blocking.

**Next:** select one new behavior-owned seam for Stage 4K.

## Stage 4J — background-watch controller static seam

**Status:** completed locally.

**Scope:** `newsnow_neon/app/controller/background_watch_controller.py`.
Existing focused coverage in `tests/test_settings_behavior.py` remained the
behavior regression guard for threshold handling and controller settings.

**Baseline:** scoped Ruff reported 16 diagnostics; scoped Pyright reported 0
errors and 0 warnings.

**Changed:** removed the unused `Optional` import, migrated legacy collection
annotations to built-in generics, ordered imports, shortened overlong
controller docstrings, and wrapped long expressions. No runtime behavior or
public import surface changed.

**Validation:** focused settings/background-watch tests passed; the full frozen
pytest suite passed; scoped Ruff is clean; scoped Pyright remains at 0 errors
and 0 warnings; `newsnow-neon --check`, `uv lock --check`, and `git diff
--check` passed.

**Measured result:** repository-wide Ruff fell from `968` to `952` diagnostics.
Pyright remains at `536` errors and `15` warnings; both repository-wide checks
remain intentionally non-blocking.

**Next:** select one new behavior-owned seam for Stage 4L.

## Stage 4K — highlight-controller static seam

**Status:** completed locally.

**Scope:** `newsnow_neon/app/controller/highlight_controller.py`.
Existing focused coverage in `tests/test_settings_behavior.py` remained the
behavior regression guard for highlight normalization, persistence, and view
refresh.

**Baseline:** scoped Ruff reported 10 diagnostics; scoped Pyright reported 0
errors and 0 warnings.

**Changed:** ordered imports, added concise public-method docstrings, wrapped
long expressions, and kept the existing highlight behavior unchanged.

**Validation:** focused highlight/settings tests passed; the full frozen pytest
suite passed; scoped Ruff is clean; scoped Pyright remains at 0 errors and 0
warnings; `newsnow-neon --check`, `uv lock --check`, and `git diff --check`
passed.

**Measured result:** repository-wide Ruff fell from `952` to `942` diagnostics.
Pyright remains at `536` errors and `15` warnings; both repository-wide checks
remain intentionally non-blocking.

**Next:** Stage 4L real-Tk GUI runtime smoke.

## Stage 4L — real-Tk GUI runtime smoke

**Status:** completed locally.

**Scope:** `tests/test_gui_runtime_smoke.py` and the existing Tk application
runtime. The test starts a separate Python process specifically to avoid the
repository's headless tkinter import stub and to exercise a real GUI backend.

**Changed:** added controlled offline service implementations for one headline,
ticker construction, persistence, history, Redis, and summaries. The subprocess
starts `AINewsApp`, enters `mainloop()`, verifies the primary list and ticker,
and exits deterministically. No production GUI behavior changed.

**Validation:** the targeted GUI smoke passed; its test file is Ruff- and
Pyright-clean; the full frozen pytest suite passed; `newsnow-neon --check`,
`uv lock --check`, and `git diff --check` passed. A separate direct probe also
confirmed one offline headline rendered in the list and ticker with
`Redis: OFF`.

**Evidence boundary:** this proves real Tk construction, event-loop dispatch,
and offline rendering on the available display. It does not prove native visual
fidelity, input interaction, NewsNow, Redis, or provider behavior.

**Next:** Stage 4M visual GUI operator-flow acceptance with controlled offline
data and the revised manual checklist.

## Stage 4M — visual GUI operator-flow acceptance

**Status:** completed locally as partial.

**Scope:** controlled offline X11 acceptance at the documented default
`900×450` geometry. The runner used deterministic headlines, an empty Redis URL,
and no provider or NewsNow calls.

**Confirmed:** a real `NewsNow Neon` window was mapped at `900×450`; the
headline list, ticker, search/filter row, and action bar were readable; an
XTEST click exercised `Show Controls → Hide Controls → Show Controls`; opening
Controls exposed readable `Refresh Now` and `Clear Headline Cache` buttons
without overlap.

**Partial result:** `Appearance & Readability` and `Monitoring & Runtime`
exist in `options_panel.py` but are below the visible controls area at the
default geometry. Search/filter fields correctly remain visible when the options
panel is hidden; they are not a toggle failure.

**Evidence boundary:** visual screenshots were captured for the app window only.
The XTEST action proves one reversible click path, not general mouse/keyboard,
native-dialog, or live-service behavior. CUA window discovery remained empty
despite a healthy WSLg/X11 doctor result.

**Next:** Stage 4N settings-panel default-geometry accessibility. Do not relax
the checklist to reclassify this partial result as a pass.

## Stage 4N — settings-panel heading accessibility

**Status:** completed locally.

**Scope:** `newsnow_neon/application.py` construction order and the existing
isolated real-Tk smoke. No service, provider, persistence, or public-import
surface changed.

**RED:** the real-Tk subprocess opened Controls at `900×450` and failed with
`Monitoring & Runtime is not mapped`.

**Changed:** built the existing options panel before the existing history panel.
This removes an unused local binding and gives the two settings groups visible
space before history at the fixed default geometry.

**Validation:** the updated real-Tk smoke verifies both named heading labels
are mapped inside the root geometry, then closes Controls and verifies the
headline list remains mapped with its offline headline. Full frozen pytest,
targeted test Ruff/Pyright, `newsnow-neon --check`, `uv lock --check`, and
`git diff --check` passed.

**Static baseline:** `application.py` Ruff changed from 169 to 168 diagnostics
with no new diagnostics (the removed binding was historic `F841`); Pyright
remains 34 errors and 0 warnings before and after. These monolith baselines are
not widened into this GUI slice.

**Visual evidence:** a controlled offline X11 capture at `900×450` showed both
headings readable without overlap. A reversible XTEST close restored visible
headline rows and `Show Controls`.

**Remaining boundary:** lower `Background…` / `Text…` controls are still partly
below the open-panel edge. Stage 4O owns that separate accessibility defect.

## Stage 4O — lower-controls accessibility

**Status:** completed locally.

**Scope:** `newsnow_neon/app/views/options_panel.py` vertical spacing and the
existing isolated real-Tk smoke. No widget commands, services, persistence, or
public-import surface changed.

**RED:** the real-Tk subprocess found both color buttons mapped but vertically
clipped: actual height `11` versus requested height `29` at `900×450`.

**Changed:** removed only the settings frame's bottom padding and reduced the
three appearance-row vertical gaps from 6 to 2 pixels. The change recovers 22
pixels without adding scrolling, removing help, or changing control behavior.

**Validation:** the real-Tk smoke now requires both color buttons to be mapped,
fully requested-height, and within the root geometry; it retains Stage 4N
heading checks and closes Controls to verify the offline headline list. Full
frozen pytest, targeted test Ruff/Pyright, `newsnow-neon --check`, `uv lock
--check`, and `git diff --check` passed.

**Static baseline:** `options_panel.py` Ruff remains 43 diagnostics with no new
or removed entries; Pyright remains 39 errors and 0 warnings before and after.
These historical diagnostics are intentionally outside the GUI layout seam.

**Visual evidence:** target-only X11 capture at `900×450` showed both color
buttons fully readable with no overlap; a reversible XTEST close restored the
headline rows and action bar.

**Remaining boundary:** a still capture shows ticker text at viewport edges, but
that can be normal marquee motion. Stage 4P owns classification before any
Ticker change.

## Stage 4P — ticker-boundary classification

**Status:** completed locally; no production code changed.

**Scope:** controlled real-Tk observation plus paired target-only X11 captures.
No user settings, native dialogs, services, providers, Redis, or ticker code
were touched.

**Evidence:** with one offline headline, the primary ticker moved from `852` to
`842` to `832` pixels and the full ticker from `865` to `860` to `855` across
successive 250 ms samples. That is exactly the expected 5 animation cycles at
50 ms with configured speeds 2 and 1. Two X11 captures one second apart also
showed matching leftward shifts of the visible text.

**Decision:** the edge clipping seen in a still is a normal marquee frame, not
persistent truncation. No ticker change or new regression test is warranted.

**Resolution:** Stage 4Q completed the temporary-store appearance persistence
round-trip; the next boundary is Stage 4R native chooser cancel-path behavior.

## Stage 4Q — custom appearance round-trip

**Status:** completed locally.

**Scope:** `newsnow_neon/app/ui/ui_helpers.py` custom-color application and the
isolated real-Tk smoke. The test uses two fresh subprocesses with one temporary
settings file and local service doubles; no native dialog or user settings path
is used.

**RED:** the writer process persisted `Custom`, speed `7`, background `#123456`,
and text `#fedcba`. A fresh verifier restored the primary ticker but failed on
the full ticker colors.

**Changed:** custom-color updates now call `set_colors` for the full ticker both
when applying selected custom values and when rebuilding the custom profile from
persisted settings.

**Validation:** the new cross-process real-Tk test writes through supported
appearance behavior, restarts against the same temporary store, and asserts
profile, speed, plus background/text on both tickers. Full frozen pytest,
targeted test Ruff/Pyright, `newsnow-neon --check`, `uv lock --check`, and
`git diff --check` passed.

**Static baseline:** `ui_helpers.py` Ruff remains 13 diagnostics with no new or
removed entries; Pyright remains 219 errors and 0 warnings before and after.
These historical diagnostics are intentionally outside this bounded fix.

**Visual evidence:** a fresh target-only X11 window confirmed both ticker bands
share the restored dark-blue background and pale-pink text, while offline rows
and the action bar remain readable without overlap.

**Resolution:** Stage 4R recorded no-op state but could not visibly map or
capture the chooser; Stage 4S is the remaining desktop-evidence boundary.

## Stage 4R — native color-chooser cancel path

**Status:** completed locally as partial evidence; no production code changed.

**Scope:** a real Tk app with offline headline doubles and a temporary custom
settings store. Target-only X11 geometry identified the `Background…` and
`Text…` controls; focus + XTest delivered their real button paths. No color was
selected, no user settings path was used, and no service/provider was called.

**Observed:** after focusing the Tk client and clicking `Background…`, X11
exposed a short-lived `NewsNow Neon` Tk `Toplevel` (`259×68`). It was already
unmapped before inspection; `import -window` could not capture it. Repeating the
focused `Text…` path did not yield a viewable chooser or visible Cancel control.
The host therefore does not support a claim that either native dialog was
visibly opened or cancelled.

**No-op evidence:** after both attempts, both ticker bands retained `#123456`
background and `#fedcba` text under `Custom`; the temporary settings JSON exactly
matched its post-startup baseline.

**Decision:** do not change chooser code or fake a native dialog. Stage 4R
closes as partial WSLg evidence, with dialog visibility and Cancel behavior
explicitly unverified.

**Resolution:** Stage 4S completed visible operator confirmation and the
controlled runner's no-op verification; the next boundary is GUI seam selection.

## Stage 4S — visible native chooser cancel confirmation

**Status:** completed locally; no production code changed.

**Scope:** a human operator used the controlled offline Tk window with a
temporary custom settings store. The operator visibly opened `Background…` and
`Text…`, then used each real chooser's Cancel control without choosing a color.

**No-op verification:** the runner's post-action status retained `Custom`,
`#123456` background, and `#fedcba` text on both ticker bands; its temporary
settings JSON matched the post-startup baseline. The temporary runner, store,
and status artifact were then removed.

**Evidence boundary:** visibility and Cancel use are manual operator evidence;
the no-change state/store is automated runner evidence. No host-wide desktop
capture, user settings path, live service, Redis, or provider was used.

**Decision:** native chooser open/Cancel acceptance is complete. Do not reopen
this seam without contradictory evidence.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 4T — manual refresh real-Tk acceptance

**Status:** completed locally; no production code changed.

**Scope:** `tests/test_gui_runtime_smoke.py` runs the real Tk application in an
isolated subprocess with a temporary settings store, empty `REDIS_URL`, and
fully configured local service doubles. The initial fetch returns one headline;
the second returns a distinct headline only after the actual `Refresh Now`
button command runs.

**Acceptance:** after the first headline renders, the test finds and invokes the
real button, waits through Tk's event loop for the worker callback, and confirms
fetch calls `[False, True]`. The refreshed headline replaces the original in the
main list, primary ticker, and full ticker. The test passed on its first run, so
this slice adds missing GUI evidence rather than changing production behavior.

**Evidence boundary:** this proves the real widget command, refresh controller,
worker callback, and controlled offline rendering. It does not prove physical
pointer input, live NewsNow, Redis, provider, or user-settings behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 4U — search/filter real-Tk acceptance

**Status:** completed locally; no production code changed.

**Scope:** `tests/test_gui_runtime_smoke.py` runs the real Tk application in an
isolated subprocess with a temporary settings store, empty `REDIS_URL`, and three
deterministic local headlines across `Business` and `Technology`.

**Acceptance:** the test invokes the real `Technology` section-menu entry, types
`security` through the search entry, invokes the search `Clear` button, then
returns to `All sections`. At every state it verifies the main list, primary
ticker, and full ticker contain exactly the expected subset; no extra fetch is
started after the initial offline load.

**Evidence boundary:** this proves real widget commands, Tk variable traces, and
controlled offline rendering. It does not prove physical pointer/keyboard input,
live NewsNow, Redis, provider, or user-settings behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 4V — exclusion real-Tk acceptance

**Status:** completed locally; no production code changed.

**Scope:** `tests/test_gui_runtime_smoke.py` runs the real Tk application in an
isolated subprocess with a temporary settings store, empty `REDIS_URL`, and three
deterministic local headlines. It uses the real exclusion entry and its adjacent
`Apply` / `Clear` button commands.

**Acceptance:** `AI, ai` normalizes to persisted `['ai']`, removes the matching
headline from the main list and both tickers, and does not start another fetch.
`Clear` persists `[]` and restores all three headline views. The test passed on
its first run, so this slice adds missing GUI evidence rather than changing
production behavior.

**Evidence boundary:** this proves real widget commands, settings-store writes,
and controlled offline rendering. It does not prove physical pointer/keyboard
input, live NewsNow, Redis, provider, or user-settings behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 4W — summary fallback real-Tk acceptance

**Status:** completed locally; repaired one production binding.

**RED:** after a controlled list-row selection, `open_selected_headline()` raised
`NameError` because it referenced an undefined `resolve_article_summary` name;
the real summary Toplevel was never created.

**Changed:** the `SummaryWindow` now receives
`app_services.resolve_article_summary`, the configured stable service proxy.

**Acceptance:** a generated real-Tk list selection sets the normal selected-row
state, then the normal selected-row open path creates `SummaryWindow`. A local
resolver returns `SummaryResolution(issue='article_fetch_failed')`; the window
renders the fallback body and the bounded unavailable-article status. No network,
provider, Redis, or user settings are used.

**Validation:** the expanded real-Tk smoke passes. Scoped Ruff/Pyright show
pre-existing `application.py` debt (Ruff 167 diagnostics; Pyright 33 errors),
while the test module is Ruff-clean and Pyright-clean; no new diagnostic was
introduced at the changed proxy call.

**Evidence boundary:** this proves generated selection, the selected-row summary
path, Toplevel construction, and controlled fallback rendering. It does not prove
physical double-click input, live NewsNow, Redis, provider, or user-settings
behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 4X — highlight real-Tk fan-out

**Status:** completed locally; repaired one production fan-out defect.

**RED:** a real `Apply` persisted `AI:#123456` and recolored the list, but both
tickers retained prior segment colors (`#FFD54F` and `#FFD60A`).

**Changed:** `HighlightController.refresh_views_for_update()` now calls the
existing renderer with `update_tickers=True`, so the same rule application
recreates ticker headline segments with current highlight colors.

**Acceptance:** a temporary-store offline app applies `AI:#123456` through the
actual entry/button, then verifies the canonical stored value, list color tag,
both ticker segment colors, enabled `Keyword Heatmap` button, and a heatmap data
set containing the expected `AI` match. No network, Redis, provider, or user
settings are used.

**Validation:** expanded real-Tk smoke plus the `highlight_controller` and GUI-test
Ruff/Pyright scopes are green. `tests/test_settings_behavior.py` retains 59 Ruff
and 7 Pyright legacy diagnostics, none at the updated render-call expectation;
full frozen pytest, `uv lock --check`, and `newsnow-neon --check` pass.

**Evidence boundary:** this proves widget commands, persistence, list/ticker
fan-out, and heatmap rendering with deterministic offline data. It does not prove
physical pointer/keyboard input, live NewsNow, Redis, provider, or user-settings
behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 4Y — controls visibility real-Tk round-trip

**Status:** completed locally; no production code changed.

**Scope:** `tests/test_gui_runtime_smoke.py` runs two fresh real-Tk subprocesses
against one temporary settings store, with deterministic offline headline data,
empty `REDIS_URL`, and local service doubles.

**Acceptance:** the first process invokes the real `Show Controls` and `Hide
Controls` commands, verifies `options_visible=True` then `False`, and checks the
compact summary text `Last refresh: offline`. It normalizes the temporary window
geometry before the restart verifier so geometry persistence cannot mask the
visibility contract. The second process restores `Show Controls`, an unmapped
options container, a mapped status-summary label, and a non-empty summary value.

**Validation:** expanded real-Tk smoke, full frozen pytest, GUI-test Ruff/Pyright,
`uv lock --check`, and `newsnow-neon --check` pass.

**Evidence boundary:** this proves real widget commands, persistence across fresh
processes, and compact summary restoration. It does not prove physical pointer or
keyboard input, live NewsNow, Redis, provider, or user-settings behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 4Z — auto-refresh real-Tk round-trip

**Status:** completed locally; no production code changed.

**Scope:** `tests/test_gui_runtime_smoke.py` runs two fresh real-Tk subprocesses
against one temporary settings store, deterministic offline headline data, empty
`REDIS_URL`, and local service doubles.

**Acceptance:** the writer opens Controls, invokes the actual `Auto Refresh
Timer` checkbutton to disable the timer, invokes the real cadence spinbox from
five to six minutes, then re-enables the timer. It verifies persisted values,
cleared or recreated `_refresh_job` and `_countdown_job`, and the corresponding
`Next refresh` status. The verifier restores the enabled six-minute timer in a
fresh process, then invokes the real checkbutton to disable it and verifies the
same persisted and scheduler-state transition.

**Validation:** the new real-Tk acceptance passes. The temporary writer records
`900×450` geometry before closing so the fresh verifier cannot inherit a
transient unmapped `1×1` window. No production code was needed.

**Evidence boundary:** this proves real widget commands, temporary-store
persistence, and Tk scheduler/status transitions. It does not prove physical
pointer or keyboard input, an elapsed minute firing a refresh, live NewsNow,
Redis, provider, or user-settings behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 5 — background-watch real-Tk round-trip

**Status:** completed locally; no production code changed.

**Scope:** `tests/test_gui_runtime_smoke.py` runs two fresh real-Tk subprocesses
against one temporary settings store, deterministic offline headlines, empty
`REDIS_URL`, and local service doubles.

**Acceptance:** the writer starts with a controlled threshold of two, invokes the
real spinbox down to one, then enables the actual `Background Watch` checkbutton.
The test confirms persistence and initial scheduling, accelerates the already
selected scheduler through its existing zero-delay wrapper, and observes a local
unseen headline trigger one forced refresh into the list. The fresh verifier
restores the enabled threshold-one watcher and disables it through the real
checkbutton, confirming persisted and cleared scheduler state.

**Validation:** the new real-Tk acceptance passes. The temporary writer records
`900×450` geometry before closing so the fresh verifier cannot inherit a
transient unmapped `1×1` window. No production code was needed.

**Evidence boundary:** this proves real widget commands, temporary-store
persistence, scheduled watcher state, and a controlled threshold-refresh path.
It does not prove physical pointer or keyboard input, the natural 15-second or
90-second watcher delays, live NewsNow, Redis, provider, or user-settings
behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 6 — logs visibility real-Tk round-trip

**Status:** completed locally; repaired one production layout/restore defect.

**RED:** at default `900×450`, the real `Show Logs` command persisted
`log_visible=True` and changed its label to `Hide Logs`, but the packed log frame
remained unmapped at `1×1`. A larger window proved the panel itself was valid;
the defect was available layout space plus restore ownership.

**Changed:** `toggle_logs()` now hides Controls before packing the log frame.
Settings application always packs or unpacks the frame from persisted
`log_visible`, rather than treating the pre-apply boolean as proof of rendered
state.

**Acceptance:** the writer uses the actual `Show Logs` button and verifies a
mapped log frame, hidden Controls, and persisted flags. A fresh verifier restores
that state, reopens Controls through its real command, then invokes `Hide Logs`
and confirms the panel is unmapped and persistence is false.

**Validation:** the new real-Tk acceptance passes at `900×450`. No user settings,
NewsNow, Redis, or provider path was used.

**Evidence boundary:** this proves widget commands, default-geometry panel
visibility, and temporary-store persistence. It does not prove physical pointer
or keyboard input, live services, provider logging, or user-settings behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 7 — cache-clear real-Tk acceptance

**Status:** completed locally; no production code changed.

**Scope:** `tests/test_gui_runtime_smoke.py` runs the real Tk application with a
temporary settings store, empty `REDIS_URL`, deterministic offline headline data,
and a local `clear_cached_headlines` double.

**Acceptance:** after opening Controls, the test invokes the actual `Clear
Headline Cache` button. It waits through Tk callbacks for exactly one double call,
the controlled completion status, and a `Redis: OFF` meter. This covers the real
button, daemon worker, callback, and operator status path without Redis.

**Validation:** the new real-Tk acceptance passes. No user settings, NewsNow,
Redis, or provider path was used.

**Evidence boundary:** this proves controlled worker/callback wiring and status
rendering. It does not prove a deployed Redis deletion, physical pointer input,
or user-settings behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 8 — info-window real-Tk acceptance

**Status:** completed locally; no production code changed.

**Acceptance:** a controlled real-Tk process invokes the actual `Info` button,
then verifies a mapped `AppInfoWindow`, canonical `About NewsNow Neon` title, and
window existence. No user settings, NewsNow, Redis, or provider path was used.

**Evidence boundary:** this proves button-to-Toplevel wiring and metadata window
construction, not physical pointer input or external-service behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 9 — mute-keyword real-Tk acceptance

**Status:** completed locally; repaired one production binding defect.

**RED:** the real Mute Keyword button called a missing instance helper instead of
`_extract_keyword_for_mute_fn`, raising `AttributeError` before persistence.

**Acceptance:** a controlled real-Tk process selects a headline, invokes Mute
Keyword, and verifies the derived `regulation` exclusion persists in a temporary
store while the list and both tickers remove the muted headline.

**Validation:** focused acceptance and full frozen pytest pass. No user settings,
NewsNow, Redis, or provider path was used.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 10 — mute-source real-Tk acceptance

**Status:** completed locally; no production code changed.

**Acceptance:** a controlled real-Tk process rendered three offline headlines,
selected the row whose source was `example.org`, and invoked the actual `Mute
Source` button. A local final-URL resolver stub returned
`https://www.example.org/article`; the action persisted `['example.org']` to a
temporary store and removed only the selected item from the list, primary ticker,
and full ticker. The initial offline fetch remained the only fetch.

**Validation:** focused real-Tk acceptance, full frozen pytest, scoped Ruff and
Pyright on the GUI test, `uv lock --check`, and `newsnow-neon --check` passed.
No user settings, NewsNow, Redis, or provider path was used.

**Evidence boundary:** this proves generated list selection, real widget-command
wiring, local resolver-worker completion, temporary-store persistence, and
rendered fan-out. It does not prove physical pointer/keyboard input, live
redirect resolution, NewsNow, Redis, or provider behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 11 — History 24h real-Tk acceptance

**Status:** completed locally; no production code changed.

**Acceptance:** a controlled real-Tk process used local Redis-presence and
history-service doubles, opened Controls, and invoked the actual `Refresh
History` button. It loaded one deterministic snapshot, activated the real
history-list selection, confirmed the historical list state with live tickers
continuing, then invoked `Return to Live` and verified the prior live list
restored without another fetch.

**Validation:** focused real-Tk acceptance, full frozen pytest, scoped Ruff and
Pyright on the GUI test, `uv lock --check`, and `newsnow-neon --check` passed.
No user settings, live Redis, NewsNow, or provider path was used.

**Evidence boundary:** this proves generated history-list selection, real
widget-command wiring, local history-worker completion, list/ticker state, and
live-list restoration. It does not prove physical pointer/keyboard input, a
deployed Redis service, live NewsNow, or provider behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 12 — Redis Stats real-Tk acceptance

**Status:** completed locally; no production code changed.

**Acceptance:** a controlled real-Tk process used local Redis-presence and
metrics doubles, invoked the actual `Redis Stats` button, verified a mapped
`RedisStatsWindow` with deterministic headline and TTL values, then invoked its
real `Close` control and verified cleanup.

**Validation:** focused real-Tk acceptance, full frozen pytest, scoped Ruff and
Pyright on the GUI test, `uv lock --check`, and `newsnow-neon --check` passed.
No user settings, deployed Redis, NewsNow, or provider path was used.

**Evidence boundary:** this proves the button, local metrics-worker callback,
window rendering, and close lifecycle. It does not prove physical input, a
deployed Redis service, live NewsNow, or provider behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 13 — natural Auto Refresh real-Tk acceptance

**Status:** completed locally; no production code changed.

**Scope:** `tests/test_gui_runtime_smoke.py` runs the real Tk application against
a temporary settings store, empty `REDIS_URL`, and deterministic local service
doubles. The initial state disables Auto Refresh at five minutes; the runner
opens Controls, uses the actual spinbox to select one minute, and invokes the
real timer checkbutton.

**Acceptance:** after the unaccelerated one-minute Tk `after` callback, the
second deterministic payload replaces the initial item in the main list, primary
ticker, and full ticker. The fetch sequence is exactly `[False, True]`; the
enabled timer has a new pending refresh job and is no longer in `Refreshing…`
status.

**Validation:** the focused real-Tk test passed with an 85-second subprocess
limit. It intentionally adds roughly one minute to the permanent pytest gate.
The CI pytest step now runs under Xvfb, and its exact local frozen command passed
with the complete real-Tk pack enabled. No user settings, NewsNow, Redis, or
provider path was used.

**Evidence boundary:** this proves the real controls, actual one-minute Tk timer
callback, worker/callback refresh path, rendered fan-out, and timer rearming. It
does not prove physical pointer/keyboard input, live NewsNow, deployed Redis, or
provider behavior.

**Next boundary:** select a new, behavior-owned GUI workflow before assigning
another numbered slice.

## Stage 14 — cross-font Controls and worker-log Tk safety

**Status:** completed locally; remote CI verification pending explicit push.

**RED:** the Xvfb runner exposed default `900×450` Controls clipping under
fallback fonts; a live probe measured a root requirement of 706 px. The same
timing revealed a worker-log/Tk deadlock when Background Watch was invoked while
the initial refresh worker emitted a log record.

**Changed:** showing Controls now expands only an undersized live window to its
Tk-required height while retaining its current width and position. `TkQueueHandler`
now queues formatted records; `AINewsApp` drains that queue from its Tk main
thread and cancels the drain job on normal close. No dependency, service,
provider, or persistence format changed.

**Validation:** the exact frozen Xvfb command passed locally for the whole
pytest suite. The four prior remote failures (Controls smoke, Background Watch,
Logs restore, Cache Clear) passed together; the Background Watch writer/verifier
still invokes the real checkbutton without an artificial initial-refresh wait.
The focused settings-stub tests, Ruff on the real-Tk test and `models.py`, and
Pyright on those two files passed. `ui_helpers.py` and `application.py` retain
their recorded global static-debt baseline; no broad static cleanup was added.
`uv lock --check` and both `--check` front doors passed.

**Evidence boundary:** this proves controlled real-Tk layout, worker/log queue
delivery, and offline Background Watch behavior. It does not prove physical
desktop input, live NewsNow, Redis, or provider behavior.

**Next boundary:** push only with explicit approval, then require the Xvfb CI
run for the delivered SHA to pass before selecting another GUI slice.

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

## Current compatibility decision

- Python 3.11 is the declared minimum supported runtime and the sole CI
  runtime. A later compatibility matrix is optional, not a prerequisite for the
  supported contract.

## Current doubts / to verify

- Whether external users depend on the compatibility module/package aliases.
- Whether live NewsNow, Redis, provider behavior, or physical desktop input
  needs a separately approved acceptance contract; current GUI evidence is
  controlled and offline-first.

## Current recommended next execution slice

**Select the next behavior-owned GUI workflow before assigning another stage.**
Use the desktop operator flow and known evidence gaps to choose one observable,
offline-reproducible outcome with explicit scope and non-goals; do not resume
native chooser work by default.
