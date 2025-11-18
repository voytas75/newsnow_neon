"""Pytest configuration to ensure imports resolve cleanly for tests.

- Prepend project root to sys.path so 'newsnow_neon' is importable with testpaths.
- Provide a minimal 'tkinter' stub when not installed to avoid import errors
  during package/module import that type-hints Tk classes.
"""

from __future__ import annotations

import sys
from pathlib import Path
import types


def _ensure_project_root_on_syspath() -> None:
    """Prepend repository root to sys.path for package imports."""
    tests_dir = Path(__file__).resolve().parent
    project_root = tests_dir.parent
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _inject_tkinter_stub() -> None:
    """Ensure a minimal 'tkinter' stub exists when Tkinter isn't installed.

    The codebase type-hints tk classes and imports tkinter at module import time.
    Tests that do not exercise GUI should not fail only due to missing Tk.
    This stub allows importing modules while avoiding runtime GUI usage.
    """
    if "tkinter" in sys.modules:
        return
    tk_stub = types.ModuleType("tkinter")
    # Provide minimal attributes used only in type hints; methods won't be called.
    # These placeholders prevent attribute errors in annotations or simple checks.
    class _Misc:  # noqa: N801 - match Tk naming style in hints
        pass

    class _Event:  # noqa: N801
        pass

    tk_stub.Misc = _Misc
    tk_stub.Event = _Event
    sys.modules["tkinter"] = tk_stub


_ensure_project_root_on_syspath()
_inject_tkinter_stub()