# Stable Service-Proxy Binding — Stage 3B

**Status:** completed locally
**Revision:** `c99d279`
**Updated:** 2026-08-08

## Problem closed

Controllers and UI helpers imported service callables directly from
`newsnow_neon.app.services` before legacy startup configured concrete
implementations. The package previously replaced its exported callables during
configuration, leaving those earlier imports bound to placeholder functions.

## Change

`newsnow_neon/app/services/__init__.py` now owns stable public dispatch proxies
and private implementation slots. `configure_app_services()` updates only the
slots; it does not replace exported functions.

Consequences:

- direct imports captured before configuration dispatch to the configured
  implementation afterward;
- dynamic `app_services.<name>` access continues to dispatch correctly;
- the existing export names remain unchanged;
- `newsnow_neon/app/services.py` remains in place pending a separate external
  compatibility decision.

## Regression evidence

`tests/test_service_bindings.py` reloads the package, captures
`fetch_headlines` before configuration, configures deterministic fakes, and
asserts both the captured import and current package access call the configured
implementation.

## Local verification

```bash
uv run --extra dev --frozen pytest tests/test_service_bindings.py tests/test_bootstrap.py -q
uv run --extra dev --frozen pytest -q
uv run --extra dev --frozen ruff check newsnow_neon/app/services/__init__.py tests/test_service_bindings.py
uv run --extra dev --frozen pyright newsnow_neon/app/services/__init__.py tests/test_service_bindings.py
python3 -m py_compile newsnow_neon/app/services/__init__.py
```

All listed checks passed locally. Remote CI verification remains pending until a
user-directed push.
