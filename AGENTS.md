# NewsNow Neon — Agent Contract

## Scope and sources of truth

- Product direction: `docs/product-ssot.md`.
- Current delivery order: `PLAN.md`.
- Enforceable scope, budgets, and approval boundaries: `BOUNDS.md`.
- Detailed completed-slice evidence: `docs/operational-plan.md`.
- User direction overrides repository documents.

Read the relevant control documents before a material change. If they conflict
or a requirement is ambiguous, stop and ask rather than infer a scope change.

## Repository map

- `newsnow_neon/`: application code; `main.py` and `__main__.py` are entrypoints.
- `newsnow_neon/legacy_app.py`: active legacy implementation boundary; change it
  only through a focused, tested seam.
- `tests/`: pytest suite and offline fixtures.
- `.github/workflows/ci.yml`: minimal remote pytest gate.
- `docs/`: product SSOT and operational evidence.

Do not treat the parallel `app/services.py` + `app/services/` or
`app/controller.py` + `app/controller/` surfaces as removable without an
import-consumer inventory and an explicit compatibility decision.

## Canonical commands

```bash
# deterministic development environment
uv sync --extra dev --frozen

# blocking local and remote gate
uv run --extra dev --frozen pytest -q

# targeted quality checks for a touched seam
uv run --extra dev --frozen ruff check <files-or-scope>
uv run --extra dev --frozen pyright <files-or-scope>

# runtime readiness, without GUI launch
uv run newsnow-neon --check

# repository integrity
git diff --check
git status --short --branch
```

Use `pytest`, Ruff, and Pyright. Do not reintroduce Black or Mypy as active
project tools. Pytest is the only blocking CI gate until a bounded Ruff/Pyright
scope is deliberately made green. Do not conceal known global static debt with
blanket ignores or broad `type: ignore`.

## Working loop

1. Inspect status and relevant docs.
2. State and keep a small slice within `BOUNDS.md`.
3. For behavior changes: write or extend a focused test first, observe RED,
   implement the smallest fix, then verify GREEN.
4. Run the frozen full test suite plus targeted Ruff/Pyright.
5. Update `PLAN.md`, `BOUNDS.md`, or the SSOT only when the operating contract
   or next delivery step changed.
6. Make a scoped local commit after verification. Push only when the user asks.

## Documentation rules

- Keep `PLAN.md`, `BOUNDS.md`, and this file aligned with the actual workflow.
- Update `docs/product-ssot.md` and `docs/operational-plan.md` when product
  direction, verified stage status, or the active next slice changes.
- Update `CHANGELOG.md` for shipped behavior or durable operational contract
  changes; do not add speculative claims.

## Ask first

- Exceeding the current file/line budget.
- Adding a dependency, a new service, or provider-backed/live-network testing.
- Changing public imports, compatibility aliases, branch protection, secrets,
  CI permissions, or GitHub workflow scope.
- Removing or renaming a module/package boundary.
- Pushing, merging, tagging, or publishing.

## Never

- Replace unrelated local work or force-push.
- Run broad auto-formatting or repo-wide static cleanup as collateral work.
- Claim GUI, live NewsNow, Redis, or provider behavior from offline tests alone.
- Record secrets in source, fixtures, logs, or documentation.
