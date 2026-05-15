# Manual GUI Smoke Checklist

Updates: v0.53.2 - 2026-05-15 - Added bounded manual smoke checklist for operator-control wording/layout verification.

## Scope
Bounded visual verification for the operator-control wording slice only.
Do not evaluate behavior changes here; this checklist is only for layout/copy regressions.

## Preconditions
- Run NewsNowNeon in a desktop session with Tk support and GUI display access.
- Start from the current working tree for the bounded operator-control slice.

## Launch
```bash
python -m newsnow_neon
```

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
