"""Package command‑line entrypoint.

Enables running the application with:

    python -m newsnow_neon

or, once installed (via the console‑script declared in *pyproject.toml*), simply:

    newsnow-neon
"""

from __future__ import annotations

from .main import main


def _run() -> None:  # pragma: no cover – thin wrapper
    """Invoke :pyfunc:`newsnow_neon.main.main`."""

    main()


if __name__ == "__main__":  # pragma: no cover
    _run()

