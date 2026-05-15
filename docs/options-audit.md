# NewsNowNeon Options Audit

Status: draft  
Scope: application options and adjacent operator controls  
Updated: 2026-05-15

## Recommendation

Recommended direction:

**Treat application options as an explicit operator-control surface, not as a miscellaneous settings bucket.**

That means the next bounded product/UX slice should:
1. define the canonical option groups around operator workflows,
2. separate persistent preferences from live filters and one-shot controls,
3. tighten wording around refresh/watch behavior,
4. keep the implementation simple and incremental instead of redesigning the whole app shell.

## Why this direction

The current repo already proves that options are functionally important:
- they control monitoring cadence,
- they control background watch automation,
- they control observability/debug behavior,
- they control historical retention,
- they persist across sessions.

This aligns with the product SSOT: NewsNowNeon is a desktop operator tool for headline monitoring and triage, not just a visual Tkinter reader.

The main current weakness is not missing functionality. The main weakness is that the overall control surface is split across:
- the Options panel,
- the search/filter row,
- log visibility,
- status summary behavior,
- persisted settings hidden behind runtime state.

So the next high-value move is **clarifying the control model**, not adding more raw settings.

## Confirmed current model

### A. Persistent operator preferences
These are backed by `DEFAULT_SETTINGS` in `newsnow_neon/config.py` and persisted through `newsnow_neon/settings_store.py`:
- `ticker_speed`
- `color_profile`
- `custom_background`
- `custom_text`
- `log_visible`
- `debug_mode`
- `window_geometry`
- `litellm_debug`
- `auto_refresh_enabled`
- `auto_refresh_minutes`
- `timezone`
- `historical_cache_enabled`
- `background_watch_enabled`
- `background_watch_refresh_threshold`
- `headline_exclusions`
- `options_visible`
- `highlight_keywords`

### B. Live session controls not fully modeled as “settings panel” controls
These are user-facing controls but are not all represented inside the main Options panel:
- search query
- section filter
- exclude terms input
- log panel show/hide
- options panel show/hide
- highlight keyword apply/reset flow
- refresh action buttons / diagnostics buttons / history actions

### C. Operationally important status outputs tied to options
The app also exposes status feedback that is part of the effective options UX:
- `Next refresh`
- `Last refresh`
- `New headlines pending`
- hidden-options compact status summary

## Functional map

## 1. Appearance options

### Color profile
- UI: `app/views/options_panel.py` -> `Profile`
- Setting key: `color_profile`
- Related keys: `custom_background`, `custom_text`
- Handler: `AINewsApp._apply_color_profile()` -> `app/ui/ui_helpers.py::apply_color_profile()`
- Effect:
  - changes ticker palette,
  - supports predefined profiles and custom colors,
  - persists immediately.

### Background color / Text color
- UI: `Background Color…`, `Text Color…`
- Setting key: `custom_background`, `custom_text`
- Handler: `AINewsApp._choose_color()` -> `app/ui/ui_helpers.py::choose_color()`
- Effect:
  - updates custom ticker theme,
  - pushes profile into custom mode when needed,
  - persists immediately.

### Ticker speed
- UI: `Speed`
- Setting key: `ticker_speed`
- Handler: `AINewsApp._apply_speed()`
- Effect:
  - clamps speed to `1..20`,
  - updates ticker runtime speed,
  - persists immediately.

## 2. Monitoring cadence options

### Auto Refresh
- UI: `Auto Refresh`
- Setting key: `auto_refresh_enabled`
- Handler: `AINewsApp._toggle_auto_refresh()`
- Effect:
  - enables/disables scheduled refresh,
  - persists state,
  - reschedules jobs,
  - updates compact status summary.

### Auto Refresh interval
- UI: `Interval (min)`
- Setting key: `auto_refresh_minutes`
- Handler: `AINewsApp._update_auto_refresh_minutes()`
- Effect:
  - clamps value to `1..180`,
  - updates scheduler cadence,
  - persists immediately.

### Next refresh / Last refresh
- UI: labels in options panel and hidden-options summary
- Setting key: none directly
- Handler: countdown/state methods in `application.py`
- Effect:
  - gives operator feedback about scheduling state,
  - reduces “is auto refresh actually on?” ambiguity.

## 3. Background monitoring options

### Background Watch
- UI: `Background Watch`
- Setting key: `background_watch_enabled`
- Handler: `AINewsApp._toggle_background_watch()` -> `BackgroundWatchController`
- Effect:
  - schedules background polling,
  - tracks unseen headlines,
  - can trigger forced refresh when threshold is reached,
  - persists immediately.

### Auto-refresh threshold for unseen headlines
- UI: `Auto-refresh at: <n> unseen headlines`
- Setting key: `background_watch_refresh_threshold`
- Handler: `AINewsApp._apply_background_watch_threshold()` -> `BackgroundWatchController.apply_threshold()`
- Effect:
  - clamps threshold to `1..999`,
  - changes automation trigger point,
  - persists immediately.

### New headlines pending status
- UI: label in options row and hidden-options status summary
- Setting key: none directly
- Handler: `BackgroundWatchController.update_label()`
- Effect:
  - surfaces background watch result to operator,
  - communicates whether automation is passive or near trigger.

## 4. Observability options

### Debug Logs
- UI: `Debug Logs`
- Setting key: `debug_mode`
- Handler: `AINewsApp._toggle_debug_mode()`
- Effect:
  - changes log verbosity/handler level,
  - persists immediately.

### LiteLLM Debug
- UI: `LiteLLM Debug`
- Setting key: `litellm_debug`
- Handler: `AINewsApp._toggle_litellm_debug()`
- Effect:
  - enables/disables verbose provider-side diagnostics,
  - persists immediately.

### Log panel visibility
- UI: `Show Logs` / `Hide Logs`
- Setting key: `log_visible`
- Handler: `AINewsApp._toggle_logs()` -> `app/ui/ui_helpers.py::toggle_logs()`
- Effect:
  - changes whether logs are visible in the main window,
  - persists immediately.

## 5. History and context options

### Keep 24h History
- UI: `Keep 24h History`
- Setting key: `historical_cache_enabled`
- Handler: `AINewsApp._toggle_historical_cache()`
- Effect:
  - enables/disables historical snapshot retention,
  - updates runtime flag through `set_historical_cache_enabled(...)`,
  - refreshes history-related controls,
  - persists immediately.

### Time Zone
- UI: `Time Zone`
- Setting key: `timezone`
- Handler: `AINewsApp._on_timezone_change()` / `_apply_timezone_selection()` -> `app/ui/ui_helpers.py`
- Effect:
  - changes timestamp presentation,
  - persists immediately,
  - refreshes display labels.

## 6. Adjacent controls that should be treated as part of the same product surface

### Search
- UI: search row
- Setting key: not persisted in `DEFAULT_SETTINGS`
- Handler: `app/ui/ui_helpers.py::on_search_change()`
- Effect:
  - filters current list view live,
  - session-only operator triage control.

### Section filter
- UI: search row
- Setting key: not persisted in `DEFAULT_SETTINGS`
- Handler: `app/ui/ui_helpers.py::on_section_filter_change()`
- Effect:
  - narrows visible headlines by section,
  - session-only triage control.

### Exclude terms
- UI: search row
- Setting key: `headline_exclusions`
- Handler: `ExclusionsController.apply_exclusion_terms()`
- Effect:
  - persists exclusion list,
  - re-renders filtered list,
  - changes effective operator view over time.

### Highlight keywords
- UI: highlight panel
- Setting key: `highlight_keywords`
- Handler: `HighlightController`
- Effect:
  - persists keyword-color rules,
  - changes attention routing in the list/ticker.

### Options panel visibility
- UI: `Show Options` / `Hide Options`
- Setting key: `options_visible`
- Handler: `app/ui/ui_helpers.py::set_options_visibility()`
- Effect:
  - changes whether operator sees the full control surface or compact status summary,
  - persists immediately.

## Product reading of the current design

The current design already suggests four real operator domains:
1. **Monitor** — auto refresh, background watch, threshold, next/last refresh.
2. **Inspect** — logs, debug, LiteLLM debug, Redis/history diagnostics nearby.
3. **Triage** — search, section filter, exclusions, highlight keywords.
4. **Appearance & ergonomics** — color profile, custom colors, ticker speed, timezone.

This is stronger than the current UI wording:
- `Ticker Appearance`
- `Behavior & Timing`

Those two headings are technically correct, but they under-express the real product model.

## Recommended next slice

### Primary recommendation

**Do a bounded control-surface clarification slice, not a broad settings rewrite.**

### What to change first

1. **Define canonical groups in product language**
   - Replace purely technical group framing with operator framing, for example:
     - `Monitoring`
     - `Background Watch`
     - `History & Time`
     - `Debug & Logs`
     - `Appearance`
   - Keep implementation simple: relabel/re-group existing controls before moving logic.

2. **Separate persistent preferences from live triage controls in docs and UI language**
   - Persistent preferences:
     - auto refresh defaults,
     - background watch,
     - history retention,
     - appearance,
     - timezone,
     - debug defaults.
   - Live triage controls:
     - search,
     - section filter,
     - one-session list narrowing.
   - Hybrid controls:
     - exclusions,
     - highlight keywords.

3. **Clarify Auto Refresh vs Background Watch copy**
   - Current behavior is functionally meaningful but conceptually easy to confuse.
   - Recommended wording direction:
     - Auto Refresh = periodic timer-based refresh.
     - Background Watch = low-frequency watcher that checks for unseen headlines and can trigger refresh when threshold is reached.

4. **Keep compact hidden-options status as a first-class feature**
   - This is good operator UX already.
   - It should be treated as intentional product behavior, not a side effect of hiding the options panel.

## Suggested backlog

### Slice A — terminology and grouping
Small, safe, high-value.
- relabel option sections using operator language,
- add short helper text/tooltips where ambiguity is highest,
- keep handlers and persistence unchanged.

### Slice B — options/control-surface documentation
- sync README-DEV or a product note with the canonical options model,
- explicitly document which controls are persistent vs session-only.

### Slice C — bounded tests for options behavior
Add focused tests for:
- settings load/save round-trip,
- auto refresh interval clamping,
- background watch threshold clamping,
- options visibility persistence,
- highlight/exclusion persistence.

### Slice D — optional UI cleanup later
Only later, if needed:
- move some triage controls into a clearer “filters” area,
- decide whether log visibility belongs in options or in a separate inspect toolbar,
- decide whether advanced debug controls should be visually demoted.

## Explicit recommendation against

Do **not** do these next:
- broad rewrite of the whole Tk layout,
- repo-wide settings abstraction overhaul,
- introducing a complex preferences framework,
- moving every control into a single giant settings modal.

That would outrun the actual problem.

## Potwierdzone

- The app already has a meaningful operator-control surface.
- The most valuable next move is control-surface clarification, not feature expansion.
- The strongest product features in options are monitoring cadence, background watch, observability, and persisted workflow preferences.
- Search/filter/exclusions/highlights should be analyzed together with options, because they are part of one effective operator workflow.

## Do weryfikacji

- whether the current end-user audience prefers always-visible advanced controls or a more progressive disclosure model,
- whether Redis-related controls should be promoted as a first-class options group or remain diagnostics-adjacent,
- whether section filter/search should stay non-persistent by design.

## Proposed execution order

1. approve the control-surface clarification direction,
2. apply small UI wording/grouping changes,
3. add bounded tests around settings persistence and clamping,
4. sync README-DEV / product docs,
5. only then evaluate deeper structural cleanup.
