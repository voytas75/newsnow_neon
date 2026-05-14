"""Package command-line entrypoint.

Enables running the application with:

    python -m newsnow_neon

or, once installed (via the console-script declared in *pyproject.toml*), simply:

    newsnow-neon
"""

from __future__ import annotations

import sys
from collections.abc import Callable

main: Callable[[], None] | None = None


def _load_main() -> Callable[[], None]:
    """Load and cache the real package entrypoint lazily."""
    global main
    if main is None:
        from .main import main as loaded_main

        main = loaded_main
    return main


def _run() -> None:  # pragma: no cover – thin wrapper
    """Invoke :pyfunc:`newsnow_neon.main.main` with startup error classification."""
    try:
        _load_main()()
    except ModuleNotFoundError as exc:
        if exc.name != "tkinter":
            raise
        print(
            (
                "Tkinter is not available in this Python runtime. Install a desktop "
                "Python build with Tk support (for example `python3-tk` on some Linux "
                "distributions)."
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":  # pragma: no cover
    _run()

