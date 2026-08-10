# Quality and Security Backlog

**Status:** security refresh verified remotely; static baseline measured locally
**Updated:** 2026-08-10

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

Current measured baseline after the Python 3.11 policy update:

| Tool | Result | Scope |
|---|---:|---|
| Ruff | 958 diagnostics | repository-wide |
| Pyright | 532 errors, 15 warnings | configured `newsnow_neon` + `tests` scope |

`[tool.pyright]` in `pyproject.toml` excludes generated `build/` copies, so the
normal root `pyright` command measures this same canonical debt scope.

The detailed hotspot inventory is intentionally not treated as a single cleanup
campaign; select one behavior-owned seam at a time and remeasure its direct
scope before changing it.

## Operating decision

- Keep pytest as the sole blocking CI gate.
- Declare Python 3.11 as the minimum supported runtime and sole CI runtime.
- Keep Ruff and Pyright as visible local baselines; do not add blanket ignores
  or repo-wide autofixes.
- Treat each future static-debt slice as a single behavior-owned seam with
  its own test and scoped quality target, not as a whole-repository campaign.
- Security remote verification is complete. Stage 3C, the P0 policy decision,
  P1 service compatibility, Stage 4A–4K, and controlled real-Tk workflows through
  Stage 14 are complete; Stage 14 is also remotely verified by GitHub CI. The next
  item is selection of one unverified, behavior-owned GUI workflow.
