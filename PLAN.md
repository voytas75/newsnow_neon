# NewsNow Neon — Delivery Plan

**Status:** active
**Updated:** 2026-08-08

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

## Next ordered work

1. **Stage 3A — service-surface inventory:** map imports and runtime bindings of
   `newsnow_neon/app/services.py` and `newsnow_neon/app/services/`; make no
   deletion or rename in the inventory slice.
2. **Stage 3B — controller-surface decision:** map consumers of
   `app/controller.py` and `app/controller/`, then propose a compatibility
   decision backed by tests/search evidence.
3. **Stage 4 — bounded static-debt reduction:** work only in a proven seam;
   never start with repo-wide Ruff or Pyright cleanup.

## Explicitly deferred

- Broad GUI redesign or framework replacement.
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
