# Service Surface Inventory — Stage 3A

**Status:** completed read-only inventory
**Revision inspected:** `fc1408cc29852f7601bac161617095d92f003a58`
**Updated:** 2026-08-08

## Boundary

This inventory covers the competing internal surfaces:

- `newsnow_neon/app/services.py` — a module-level proxy registry;
- `newsnow_neon/app/services/` — a package exporting placeholder callables and
  rebinding them during `configure_app_services()`.

No production module, public import, or package boundary was changed while
collecting this evidence. No network, Redis, GUI, or provider call was made.

## Confirmed import resolution

A clean Python process resolves:

```python
import newsnow_neon.app.services as services
```

to `newsnow_neon/app/services/__init__.py`, not to `services.py`.

Therefore `services/` is the active internal import surface. `services.py` is
not selected by normal package imports; do not delete it until external
compatibility expectations are explicitly investigated.

## Binding path

| Boundary | Evidence | Result |
|---|---|---|
| Legacy implementation → package registry | `newsnow_neon/legacy_app.py:91,3230-3238` imports `configure_app_services` via `application.py` and configures the package after defining concrete legacy functions. | Concrete implementations are available for package rebinding. |
| Startup → package registry | `newsnow_neon/main.py:101-135` imports the package and invokes `configure_app_services()` again after importing `legacy_app`. | Explicit, idempotent startup binding. |
| Application runtime → package registry | `newsnow_neon/application.py:65-67,443,475-485,993` retains the package object as `app_services`. | Calls observe a later package-level rebind. |
| Controller/UI → package exports | Direct imports occur in `app/controller/background_watch_controller.py:19`, `history_controller.py:17`, `redis_controller.py:13`, `app/ui/history_ui.py:13`, and `ui_helpers.py:15`. | Import-time callable references can become stale after a later rebind. |

## Confirmed defect

A fresh-process probe imported `fetch_headlines` directly from the package,
then configured the package with a concrete fake implementation. The previously
bound callable remained the placeholder from `services/news_service.py` and
raised `NotImplementedError`.

This affects the direct-import consumers listed above because `application.py`
imports controller classes before `legacy_app.py` configures the package.
The dynamic `app_services.<name>` calls in `application.py` are not affected.

Existing `tests/test_bootstrap.py` proves package rebinding through dynamic
package access, but it does not prove that direct imports taken before binding
remain live.

## Stage 3B outcome

The stable-proxy fix is implemented locally and documented in
[`service-proxy-binding.md`](service-proxy-binding.md). The package remains the
canonical internal surface; no module/package removal decision was made.

## To verify later

- Whether any external user imports or executes `services.py` by file path.
- Whether the duplicate module should be deprecated after a compatibility
  decision, rather than merely left unreachable by normal imports.
