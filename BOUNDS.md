# NewsNow Neon — Execution Bounds

**Status:** active
**Updated:** 2026-08-09

## Governing documents

User direction overrides all repository documents. For repository work, use:

1. `docs/product-ssot.md` for product direction;
2. `PLAN.md` for current delivery order;
3. this file for enforceable execution limits;
4. `AGENTS.md` for concise agent workflow;
5. `docs/operational-plan.md` for completed-slice evidence and detailed history.

Conflicts, ambiguity, or a proposed scope change require explicit user approval.

## In scope

- Maintain the desktop NewsNow monitoring and triage workflow.
- Improve behavior through focused, offline-first regression tests.
- Make package boundaries explicit only after import-consumer evidence exists.
- Maintain reproducible setup and the minimal frozen pytest CI gate.
- Repair selected Ruff/Pyright seams only when they are directly touched and
  remain behaviorally verified.

## Out of scope without explicit approval

- New product features, framework replacement, or broad UI redesign.
- New runtime/development dependencies.
- Live provider calls, API keys, or live scraper acceptance runs.
- Repo-wide formatting, Ruff cleanup, or Pyright cleanup.
- Deleting, renaming, or merging `services.py`/`services/` or
  `controller.py`/`controller/` before an inventory and compatibility decision.
- Changing branch protection, access controls, secrets, or CI permissions.
- Pushing, merging, or publishing a release.

## Change budgets

| Slice type | Ordinary limit | Approval required before exceeding |
|---|---|---|
| Documentation-only | 7 files, 400 net lines | Larger rewrite or a new control document outside this set |
| Behavior/test seam | 5 files, 250 net lines, 1 fixture | Any additional seam, new dependency, or broader refactor |
| CI/tooling | 4 files, 200 net lines, no dependency | Runtime matrix, permissions, or new service integration |
| Package-boundary inventory | Read-only | Any rename, deletion, compatibility change, or public import change |

Mechanical changes count toward the applicable file and line limit. Do not split
one conceptual change into artificial commits to evade a bound.

## Required verification

### Documentation-only slice

```bash
git diff --check
git status --short --branch
```

### Python behavior slice

```bash
uv sync --extra dev --frozen
uv run --extra dev --frozen pytest -q
uv run --extra dev --frozen ruff check <touched-files-or-scope>
uv run --extra dev --frozen pyright <touched-files-or-scope>
git diff --check
```

Global Ruff/Pyright need not be green while their documented legacy baseline
remains. Never hide debt through blanket ignores or broad `type: ignore`.

## Agent rules

1. Read `PLAN.md`, this file, and the relevant SSOT before a material change.
2. Inspect Git status before editing; do not overwrite unrelated local work.
3. Use test-first changes for behavior fixes: establish RED, make the smallest
   fix, then verify GREEN.
4. Keep provider, network, Redis, and GUI tests mocked or fixture-based unless
   the user explicitly approves a live acceptance case.
5. Update the plan/SSOT and changelog when a completed slice changes the active
   delivery state or user-visible behavior.
6. Commit completed bounded slices locally. Do not push unless asked.
7. Report confirmed facts separately from items still to verify.

## Current immediate boundary

Stage 4Q is complete for the custom-color round-trip defect: controlled
cross-process real Tk now restores the custom profile, speed, background, and
text on both tickers through a temporary settings store. Stage 4R may only open
and cancel each native color chooser against a temporary store; it must not
choose a color, call NewsNow, Redis, or a provider, alter the user's settings
file, redesign the GUI, or change compatibility surfaces incidentally.
