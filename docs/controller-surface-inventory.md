# Controller Surface Inventory — Stage 3C

**Status:** completed read-only inventory

**Revision inspected:** `7c607df209f5a2b7c8e048c99c5a346c42d1d9da`

**Updated:** 2026-08-08

## Boundary

This inventory covers the coexisting internal paths:

- `newsnow_neon/app/controller.py` — compatibility file exporting `AINewsApp`;
- `newsnow_neon/app/controller/` — active controller package and its concrete
  controller modules.

No production module, public import, package boundary, or runtime behavior was
changed. No GUI, network, Redis, or provider call was made.

## Confirmed import resolution

A fresh interpreter resolved normal dotted imports to package initializers:

```text
newsnow_neon.app.controller -> newsnow_neon/app/controller/__init__.py
newsnow_neon.app.services   -> newsnow_neon/app/services/__init__.py
```

The sibling `controller.py` and `services.py` files are therefore not selected
by normal dotted imports. `controller.AINewsApp is application.AINewsApp` was
also confirmed in the same probe.

## Runtime and test consumers

| Surface | Evidence | Result |
|---|---|---|
| Active controller runtime | `newsnow_neon/application.py:70-80` imports nine concrete controller modules; `:250-261` instantiates them on `AINewsApp`. | The package submodules are the active runtime surface. |
| Controller package exports | `newsnow_neon/app/controller/__init__.py:12-53` lazily resolves controller classes and maps `AINewsApp` to `newsnow_neon.application`. | Package import stays lazy until a Tk-bound export is accessed. |
| Compatibility file | `newsnow_neon/app/controller.py:13-15` only re-exports `application.AINewsApp`. | It is not a second class surface. |
| Repository consumers of file path | `tests/test_bootstrap.py:105-128` explicitly loads `controller.py` by file path and asserts identity with the package export. | The file path remains regression-covered as compatibility behavior. |
| Internal normal imports of `controller.AINewsApp` | Repository search found none. | Internal runtime does not require the compatibility file. |
| Dynamic controller loading | Search found only the package's own lazy `__getattr__` and test probes. | No separate production dynamic selection of `controller.py` was found. |

## Service-boundary cross-check

The controller modules use `newsnow_neon.app.services` through the active
package surface, including direct callable imports in background-watch, history,
and Redis controllers. `app/services/__init__.py` retains stable dispatch
proxies; `tests/test_service_bindings.py` protects imports taken before startup
configuration.

The separate `services.py` file remains compatibility-only for the same reason
as `controller.py`: normal imports select the package, while file-path external
consumers cannot be observed from this repository.

## Verification

```text
uv run --extra dev --frozen pytest tests/test_bootstrap.py tests/test_service_bindings.py -q  PASS
git diff --check                                                                  PASS before documentation edits
```

The import probe confirmed both package origins and `AINewsApp` identity at the
revision above.

## Decision and next acceptance seam

**Canonical internal surfaces:** `newsnow_neon.app.controller` package and
`newsnow_neon.app.services` package.

**P0 owner decision (2026-08-08):** retain `controller.py` and `services.py` as
supported external compatibility surfaces, including file-path and historical
direct-submodule use.

This is fully evidenced for `controller.py`: its explicit file load exposes the
same `AINewsApp` object as the package export. The separate `services.py` file
maintains its own registry, however, so the selected supported contract needs a
focused P1 acceptance test and any minimal proxy/delegation correction required
to make file-path behavior match the canonical package after configuration.

No broad controller extraction or service rewrite is justified by this decision.
