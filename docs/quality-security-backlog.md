# Quality and Security Backlog

**Status:** measured locally; security lock refresh awaits remote verification
**Updated:** 2026-08-08

## Security — current bounded slice

GitHub reported 16 open Dependabot alerts. They collapse to two transitive lock
entries:

| Package | Dependency path | Previous | Local refreshed version | Highest alert severity |
|---|---|---:|---:|---|
| `aiohttp` | `newsnow-neon[llm]` → `litellm` | 3.13.5 | 3.14.3 | high |
| `soupsieve` | `newsnow-neon` → `beautifulsoup4` | 2.8.3 | 2.9.2 | high |

The lock refresh changed only those package versions; no package was added or
removed. `uv lock --check`, a frozen install including `dev` and `llm` extras,
and the full pytest suite passed locally.

**Remote closure condition:** push the lock refresh, confirm GitHub CI for its
SHA, then re-query Dependabot. The expected result is closure of all 16 alerts;
that remains **to verify** until GitHub processes the new lockfile.

## Static-quality baseline

Current measured baseline, after the Stage 3B service-binding fix:

| Tool | Result | Scope |
|---|---:|---|
| Ruff | 1,165 diagnostics | repository-wide |
| Pyright | 641 errors, 15 warnings, 68 files | repository-wide |

Largest current hotspots are intentionally not treated as a single cleanup:

- Ruff: `legacy_app.py` (281), `application.py` (169), `models.py` (85), and
  `cache.py` (59) diagnostics.
- Pyright: `app/ui/ui_helpers.py` (219), `app/ui/history_ui.py` (134), and
  `legacy_app.py` (111) errors.
- Pyright rule concentration: `reportAttributeAccessIssue` (507),
  `reportRedeclaration` (57), `reportArgumentType` (42), and
  `reportCallIssue` (27).

## Operating decision

- Keep pytest as the sole blocking CI gate.
- Keep Ruff and Pyright as visible local baselines; do not add blanket ignores
  or repo-wide autofixes.
- Treat the first future static-debt slice as a single behavior-owned seam with
  its own test and scoped quality target, not as a whole-repository campaign.
- Do not start Stage 3C package-boundary work before remote verification of the
  security lock refresh unless the user explicitly chooses to continue locally.
