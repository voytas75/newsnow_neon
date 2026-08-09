# Quality and Security Backlog

**Status:** security refresh verified remotely; static baseline measured locally
**Updated:** 2026-08-09

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

**Remote result:** CI run [#31278999184](https://github.com/voytas75/newsnow_neon/actions/runs/31278999184) passed. GitHub's Dependency Graph submitted the refreshed `uv.lock`, and all 16 alerts were recorded as fixed at 2026-08-08T21:19:36–37Z. GitHub now returns zero open Dependabot alerts.

## Static-quality baseline

Current measured baseline, after P1 service compatibility and Stage 4A–4J:

| Tool | Result | Scope |
|---|---:|---|
| Ruff | 952 diagnostics | repository-wide |
| Pyright | 536 errors, 15 warnings, 68 files | repository-wide |

The detailed hotspot inventory is intentionally not treated as a single cleanup
campaign; select one behavior-owned seam at a time and remeasure its direct
scope before changing it.

## Operating decision

- Keep pytest as the sole blocking CI gate.
- Keep Ruff and Pyright as visible local baselines; do not add blanket ignores
  or repo-wide autofixes.
- Treat the first future static-debt slice as a single behavior-owned seam with
  its own test and scoped quality target, not as a whole-repository campaign.
- Security remote verification is complete. Stage 3C, the P0 policy decision,
  P1 service compatibility, and Stage 4A–4H are complete locally; the next
  item is another bounded Stage 4 seam.
