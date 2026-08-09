# Manual GUI Smoke Checklist

Updates: v0.53.2 - 2026-05-15 - Added bounded manual smoke checklist for operator-control wording/layout verification.

## Scope
Bounded GUI acceptance for the primary desktop workflow: real Tk launch, offline
headline rendering, control visibility, and layout/copy at default geometry.

- The automated baseline is `tests/test_gui_runtime_smoke.py`, which starts the
  real Tk app in an isolated subprocess with controlled offline data.
- This checklist records visual/input evidence that the subprocess cannot prove.
- It does not establish NewsNow, Redis, provider, native-dialog, or live-network
  behavior.

## Preconditions
- Run NewsNowNeon in a desktop session with Tk support and GUI display access.
- Start from the current working tree for the bounded GUI acceptance slice.

## Automated runtime preflight
```bash
uv run --extra dev --frozen pytest -q tests/test_gui_runtime_smoke.py
```
- [ ] The isolated real-Tk smoke passes on the current desktop display.
- [ ] Its output is understood as offline GUI evidence only.

## Launch
Do not use the normal `python -m newsnow_neon` path for offline acceptance: it
starts a NewsNow refresh. Use a separately approved controlled offline runner
for a manual visual session.

## Checklist

### 1. Action bar / top-level controls
- [ ] App launches without immediate Tk/layout errors.
- [ ] The toggle button reads `Show Controls` before opening the panel.
- [ ] After opening the panel, the toggle button reads `Hide Controls`.
- [ ] Closing the panel restores `Show Controls`.
- [ ] If the status summary is empty while controls are hidden, fallback text reads `Controls hidden`.

### 2. Controls row
- [ ] Primary refresh button reads `Refresh Now`.
- [ ] Cache-clear button reads `Clear Headline Cache`.
- [ ] Button labels fit on one line and are not visually clipped.

### 3. Options / operator-control panel groups
- [ ] First group header reads `Appearance & Readability`.
- [ ] Second group header reads `Monitoring & Runtime`.
- [ ] Group headers are fully visible and do not overlap adjacent controls.

### 4. Appearance labels
- [ ] Theme selector label reads `Theme:`.
- [ ] Color buttons read `Background…` and `Text…`.
- [ ] These labels fit without clipping or awkward overlap.

### 5. Monitoring labels
- [ ] Auto-refresh checkbox reads `Auto Refresh Timer`.
- [ ] Interval label reads `Every (min):`.
- [ ] Background-watch threshold label reads `Trigger refresh at:`.
- [ ] Timezone label reads `Display Time Zone:`.
- [ ] Longer labels remain readable at the default window size.

### 6. Resize sanity
- [ ] At the default window geometry, no new label is truncated badly.
- [ ] After a modest horizontal resize smaller and larger, labels still remain usable.
- [ ] No obvious widget overlap appears after opening/closing the controls panel.

## Stage 4M controlled offline result — 2026-08-09

**status: partial**

- confirmed: real X11 window at `900×450`; offline headline list/ticker;
  `Show Controls → Hide Controls → Show Controls` via a reversible XTEST click;
  readable `Refresh Now` and `Clear Headline Cache` controls without overlap.
- failed: the two options-panel group headings are not visible at the default
  geometry. They exist in the widget implementation but are below the visible
  controls area.
- note: search/filter fields remain visible when Controls is hidden; they are
  not part of the toggled options panel.
- resolution: Stage 4N restored both heading labels, Stage 4O restored lower
  color controls, Stage 4P classified marquee movement, and Stage 4Q restored
  custom colors to both ticker bands after restart. Stage 4R leaves native
  chooser visibility and Cancel action as desktop evidence to verify.

- **Stage 4N narrow result: pass.** At `900×450`, both `Appearance &
  Readability` and `Monitoring & Runtime` are now visible after opening
  Controls; the real-Tk smoke and controlled X11 capture also confirm the full
  Controls-toggle cycle and restored headline rows after closing.
- **Stage 4O narrow result: pass.** `Background…` and `Text…` now render at
  their full requested height within the root geometry, and controlled X11
  capture confirms both are readable without overlap.
- **Stage 4P result: no defect.** Primary ticker state moved `852 → 842 → 832`
  and full ticker state `865 → 860 → 855` across controlled 250 ms samples;
  paired X11 captures showed the same leftward marquee motion. No ticker change
  is warranted.
- **Stage 4Q narrow result: pass.** A fresh Tk process restores `Custom`, speed
  `7`, `#123456` background, and `#fedcba` text on both ticker bands through a
  temporary store; target-only X11 capture confirms the shared rendering.
- **Stage 4R result: partial.** Focus + XTest reached both real color-button
  paths with no runtime/store change, but the WSLg native transient was unmapped
  and non-captureable; neither a visible chooser nor Cancel action is confirmed.

## Result Template
Use this short format when recording the outcome:

- status: pass / partial / fail
- environment: OS + Python + Tk availability
- confirmed:
  - ...
- issues:
  - ...
- screenshots: optional paths
- follow-up:
  - none / required

## Decision Rule
- **pass**: all wording is correct and no visible layout regressions are observed.
- **partial**: wording is correct but at least one label clips or needs spacing follow-up.
- **fail**: launch/layout breaks or multiple controls are visually unusable.
