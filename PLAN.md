# NewsNow Neon — Delivery Plan

**Status:** active
**Updated:** 2026-08-09

## Purpose

Deliver a trustworthy desktop tool for monitoring and triaging curated NewsNow
headlines without expanding into a general automation or LLM platform.

## Product outcome

The desktop operator can inspect curated headlines, use a ticker/list workflow,
review article summaries, and rely on predictable local startup, cache behavior,
and diagnostics.

## Confirmed baseline

- Python desktop application with supported entrypoints `python -m newsnow_neon`
  and `newsnow-neon`.
- `pytest`, Ruff, and Pyright are the retained quality tools.
- `pytest` is the sole blocking GitHub CI gate; global Ruff/Pyright debt is
  measured locally and reduced by bounded seam.
- Frozen dependency setup is canonical: `uv sync --extra dev --frozen`.
- Stage 1 operational baseline, Stage 2 product-confidence slices, and the
  Node 24 Actions refresh are pushed and verified by GitHub CI run [#31274048561](https://github.com/voytas75/newsnow_neon/actions/runs/31274048561).
- The security lock refresh is pushed and verified by CI run [#31278999184](https://github.com/voytas75/newsnow_neon/actions/runs/31278999184); GitHub now reports zero open Dependabot alerts.

## Completed delivery slices

- **Stage 1 — operational baseline:** tracked `uv.lock`, selected toolchain,
  and minimal frozen pytest CI.
- **Stage 1C — Actions runtime:** Node 24-compatible Action revisions, verified
  by CI without the deprecated Node 20 annotation.
- **Stage 2A — parsing:** fixture-based NewsNow parsing, metadata,
  deduplication, cutoff, malformed-markup, and unsafe-href coverage.
- **Stage 2B.1 — settings:** persisted refresh-interval normalization and
  malformed-settings fallback.
- **Stage 2B.2 — cache/history:** fake-Redis cache-payload and history-boundary
  coverage.
- **Stage 2B.3 — summaries:** cache, fetch failure, empty output, and provider
  failure fallback coverage.
- **Stage 3A — service-surface inventory:** confirmed that `services/` is the
  active internal import surface and found a stale direct-import binding defect
  documented in `docs/service-surface-inventory.md`.
- **Stage 3B — stable service proxies:** fixed stale direct-import bindings with
  stable package proxies and offline regression coverage.
- **Stage 3C — controller-surface inventory:** confirmed that normal imports
  select `app/controller/`, while `app/controller.py` is an identity-preserving
  compatibility file with no internal normal-import consumer. Evidence is in
  `docs/controller-surface-inventory.md`.
- **P0 — controller/service compatibility policy:** external compatibility
  surfaces are retained as supported.
- **P1 — service compatibility contract:** made explicit `services.py`
  file-path loads re-export the canonical stable package proxies; focused
  regression coverage proves dispatch after package configuration.
- **Stage 4A — mute-action seam:** reduced the `app/actions.py` Ruff baseline
  from 3 diagnostics to 0 and added focused helper regression coverage.
- **Stage 4B — filtering seam:** reduced the `app/filtering.py` Ruff baseline
  from 12 diagnostics to 0 and added focused exclusion/filtering coverage.
- **Stage 4C — rendering seam:** reduced the `app/rendering.py` Ruff baseline
  from 16 diagnostics to 0 and added focused age-bucket/metadata coverage.
- **Stage 4D — environment logging seam:** reduced the
  `app/helpers/env_helpers.py` Ruff baseline from 3 diagnostics to 0 and added
  focused secret-masking coverage.
- **Stage 4E — news-service seam:** reduced the
  `app/services/news_service.py` Ruff baseline from 7 diagnostics to 0 and
  added focused unconfigured-provider coverage.
- **Stage 4F — cache-service seam:** reduced the
  `app/services/cache_service.py` Ruff baseline from 2 diagnostics to 0 and
  added focused unconfigured-provider coverage.
- **Stage 4G — refresh-controller seam:** reduced the
  `app/controller/refresh_controller.py` Ruff baseline from 2 diagnostics to 0
  and added focused manual-refresh orchestration coverage.
- **Stage 4H — auto-refresh-controller seam:** reduced the
  `app/controller/auto_refresh_controller.py` Ruff baseline from 1 diagnostic
  to 0 and added focused pending-job cancellation coverage.
- **Stage 4I — legacy helper consolidation:** removed 57 redundant top-level
  helper definitions from `legacy_app.py`, retaining the final active
  implementations and adding an AST structural regression test plus offline
  helper-contract coverage. The global measured baselines fell from Ruff
  `1,091` to `968` diagnostics and Pyright `641` to `536` errors; neither is
  yet a blocking repository-wide gate.
- **Stage 4J — background-watch controller seam:** reduced the
  `app/controller/background_watch_controller.py` Ruff baseline from 16
  diagnostics to 0 with no runtime behavior change. Existing focused
  background-watch/settings coverage remained green; scoped Pyright stayed at
  0 errors and 0 warnings. The repository-wide Ruff baseline is now `952`
  diagnostics; Pyright remains `536` errors and `15` warnings.
- **Stage 4K — highlight-controller seam:** reduced the
  `app/controller/highlight_controller.py` Ruff baseline from 10 diagnostics
  to 0 with no runtime behavior change. Existing focused highlight/settings
  coverage remained green; scoped Pyright stayed at 0 errors and 0 warnings.
  The repository-wide Ruff baseline is now `942` diagnostics; Pyright remains
  `536` errors and `15` warnings.
- **Stage 4L — real-Tk GUI smoke:** added an isolated subprocess regression
  test that starts the real Tk application on an available display, renders an
  offline headline through its event loop, and verifies both the main list and
  ticker. It stubs NewsNow, Redis, and provider-facing services; it does not
  claim live integration acceptance.
- **Stage 4M — visual GUI operator-flow acceptance:** verified the offline
  list/ticker and reversible `Show Controls → Hide Controls → Show Controls`
  cycle on a real X11 window. The result is partial: at the default `900×450`
  geometry, the options-panel group headings are not visible after opening
  Controls. The defect is carried into Stage 4N rather than hidden by relaxing
  the checklist.
- **Stage 4N — settings-panel heading accessibility:** moved the existing
  options panel before history so `Appearance & Readability` and `Monitoring &
  Runtime` are visible at `900×450`. The real-Tk smoke now verifies both heading
  geometry and the complete controls-toggle cycle. The remaining lower-controls
  overflow is deferred to Stage 4O.
- **Stage 4O — lower-controls accessibility:** compacted only vertical padding
  within the existing appearance rows. `Background…` and `Text…` now retain
  their full requested height at `900×450`; the real-Tk smoke protects this,
  the Stage 4N headings, and the close-state list. Ticker edge clipping was left
  for the completed Stage 4P evidence classification.
- **Stage 4P — ticker-boundary classification:** controlled real-Tk state moved
  primary ticker text `852 → 842 → 832` and full ticker text `865 → 860 → 855`
  across 250 ms samples; paired X11 captures one second apart showed matching
  leftward motion. Edge clipping is normal marquee behavior, not a defect; no
  ticker code changed.
- **Stage 4Q — custom appearance round-trip:** a cross-process real-Tk contract
  found that custom colors restored only to the primary ticker. Both immediate
  custom-color application and store restoration now apply colors to both
  tickers; a fresh X11 capture confirms the shared custom rendering.
- **Stage 4R — native chooser cancel path:** focus + XTest reached both real
  color-button paths against a temporary store, but WSLg exposed only an
  unmapped transient and no captureable chooser or verifiable Cancel control.
  Runtime colors and the temporary store remained unchanged; native-dialog
  acceptance remains partial and needs visible desktop evidence.
- **Stage 4S — visible native chooser cancel confirmation:** a human operator
  visibly opened and cancelled both real choosers against the controlled temporary
  store. The runner then confirmed unchanged `Custom` values on both tickers and
  unchanged persisted settings. No color was selected; no code changed.
- **Stage 4T — manual refresh real-Tk acceptance:** an isolated subprocess uses
  two deterministic offline payloads, invokes the actual `Refresh Now` button,
  and verifies the completed second result replaces the first in the list and
  both ticker bands. No production code, user settings, NewsNow, Redis, or
  provider path was used.
- **Stage 4U — search/filter real-Tk acceptance:** a three-headline offline
  fixture uses the actual section-menu, search-entry, and Clear-button commands
  to prove the list and both ticker bands narrow and restore together. No
  production code, user settings, NewsNow, Redis, or provider path was used.
- **Stage 4V — exclusion real-Tk acceptance:** a three-headline offline fixture
  uses actual exclusion Apply/Clear commands and a temporary settings store to
  prove persisted exclusions and restored list/ticker rendering. No production
  code, user settings, NewsNow, Redis, or provider path was used.
- **Stage 4W — summary fallback real-Tk acceptance:** a controlled selection opens
  a real summary Toplevel with a deterministic fallback result; the missing
  resolver binding was repaired through the configured service proxy. No user
  settings, NewsNow, Redis, or provider path was used.
- **Stage 4X — highlight real-Tk fan-out:** a controlled Apply persists a custom
  highlight, refreshes matching list/ticker segments, and opens a matching keyword
  heatmap; a stale-ticker fan-out defect was repaired. No user settings, NewsNow,
  Redis, or provider path was used.
- **Stage 4Y — controls visibility real-Tk round-trip:** two fresh offline Tk
  processes use the actual Show/Hide Controls command, persist `options_visible`,
  and verify the compact hidden status summary on restore. No production code,
  user settings, NewsNow, Redis, or provider path was used.
- **Stage 4Z — auto-refresh real-Tk round-trip:** two fresh offline Tk processes
  use the actual `Auto Refresh Timer` checkbutton and `Every (min)` spinbox,
  persist timer state and cadence in a temporary store, and verify scheduled or
  cleared Tk job IDs plus the corresponding `Next refresh` status. No production
  code, user settings, NewsNow, Redis, or provider path was used.
- **Stage 5 — background-watch real-Tk round-trip:** two fresh offline Tk
  processes use the actual watcher checkbutton and threshold spinbox, persist
  their temporary-store values, and verify unseen-headline threshold refresh plus
  scheduled or cleared watcher state. No production code, user settings, NewsNow,
  Redis, or provider path was used.
- **Stage 6 — logs visibility real-Tk round-trip:** repaired the default-geometry
  false-success path where `Hide Logs` could label an unmapped panel. `Show Logs`
  now hides Controls before displaying logs, and fresh-process restore respects
  persisted `log_visible`. No user settings, NewsNow, Redis, or provider path was
  used.
- **Stage 7 — cache-clear real-Tk acceptance:** the actual `Clear Headline Cache`
  button reaches its worker callback, emits a controlled completion status, and
  refreshes the disabled Redis meter without a Redis connection. No production
  code, user settings, NewsNow, Redis, or provider path was used.
- **Stage 8 — info-window real-Tk acceptance:** the actual `Info` button opens a
  mapped `AppInfoWindow` with canonical metadata; no production code, user
  settings, NewsNow, Redis, or provider path was used.
- **Stage 9 — mute-keyword real-Tk acceptance:** repaired the missing keyword
  helper binding; real row selection and `Mute Keyword` now persist the derived
  exclusion and filter the list plus both tickers without live services.
- **Stage 10 — mute-source real-Tk acceptance:** a controlled real-Tk process
  selected a headline, invoked the actual `Mute Source` button, resolved its
  final source through a local stub, then verified the temporary-store exclusion
  filters the list and both ticker bands without another fetch or live service.

## Next ordered work

1. **Stage 11 — History 24h real-Tk acceptance:** with a local Redis-presence
   stub and deterministic historical snapshot, invoke `Refresh History`, select
   the snapshot, then invoke `Return to Live`. Verify history/list state, the
   intended live-ticker continuity, and restoration of the prior live list
   without a live Redis, NewsNow, provider, or user-settings path.
2. **Compatibility maintenance:** preserve the controller and services
   compatibility tests when later seams touch package loading or startup.

## Explicitly deferred

- Broad GUI redesign or framework replacement. Targeted GUI runtime and visual
  acceptance work remains in scope because the desktop workflow is the primary
  product surface.
- Live-network scraper acceptance tests as a substitute for fixtures.
- Live provider-backed summary acceptance without case-by-case approval.
- Repository-wide Ruff/Pyright cleanup.
- Removal of compatibility module/package surfaces without import-consumer
  evidence and regression coverage.

## Definition of done for each behavior slice

- Scope fits `BOUNDS.md` or has explicit approval to exceed it.
- Behavior has a focused regression test before or alongside the smallest fix.
- Frozen full pytest suite passes.
- Ruff and Pyright are run on the touched scope; remaining baseline debt is
  recorded rather than hidden.
- `git diff --check` passes; the slice has a local commit.
- Push and remote CI verification occur only when explicitly requested.

## Sources of truth

- Product direction and broader rationale: `docs/product-ssot.md`.
- Stage history and detailed validation evidence: `docs/operational-plan.md`.
- Scope and execution controls: `BOUNDS.md`.
- Agent working contract: `AGENTS.md`.
