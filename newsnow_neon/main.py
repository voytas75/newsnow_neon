"""Application entrypoint wiring for NewsNow Neon.

The full Tkinter orchestration still lives in the packaged legacy
``legacy_app.py`` module. The goal is to migrate that logic into dedicated
layers over time.

Updates: v0.49.1 - 2025-01-07 - Added metadata factory and stub main routine.
Updates: v0.49.2 - 2025-10-29 - Switched to packaged legacy module and
removed reliance on root-level script.
Updates: v0.49.4 - 2025-10-30 - Hardcoded author and support metadata to
avoid env dependencies.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

logger = logging.getLogger(__name__)

APP_VERSION = "0.53"
TKINTER_IMPORT_ERROR_MESSAGE = (
    "Tkinter is not available in this Python runtime. Install a desktop Python build "
    "with Tk support (for example `python3-tk` on some Linux distributions)."
)
HEADLESS_DISPLAY_ERROR_MESSAGE = (
    "NewsNowNeon cannot start the GUI in this environment because no graphical display "
    "is available. Run it from a desktop session with DISPLAY/GUI access."
)


@dataclass(frozen=True)
class AppMetadata:
    """App metadata used by the startup seam and info surfaces."""

    name: str
    version: str
    author: str
    donate_url: str
    description: str


APP_METADATA = AppMetadata(
    name="NewsNow Neon",
    version=f"v{APP_VERSION}",
    author="https://github.com/voytas75",
    donate_url="https://ko-fi.com/voytas",
    description=(
        "Tkinter desktop dashboard for curated NewsNow headlines with cached summaries "
        "and live configuration controls."
    ),
)


class DiagnosticCheck(TypedDict):
    """Single readiness-check result for diagnostics mode."""

    name: str
    status: Literal["confirmed", "failed", "optional"]
    detail: str
    required: bool


class StartupDiagnostics(TypedDict):
    """Structured startup-readiness report for terminal diagnostics."""

    python_version: str
    app_version: str
    checks: list[DiagnosticCheck]
    required_ready: bool
    required_failures: list[str]


def load_app_class() -> type[Any]:
    """Load the Tk app class while classifying missing Tk support explicitly."""
    try:
        legacy_app = importlib.import_module("newsnow_neon.legacy_app")
    except ModuleNotFoundError as exc:
        if exc.name == "tkinter":
            raise RuntimeError(TKINTER_IMPORT_ERROR_MESSAGE) from exc
        raise

    return cast(type[Any], legacy_app.AINewsApp)


def detect_tkinter_runtime() -> None:
    """Verify that the runtime can import tkinter."""
    try:
        importlib.import_module("tkinter")
    except ModuleNotFoundError as exc:
        if exc.name == "tkinter":
            raise RuntimeError(TKINTER_IMPORT_ERROR_MESSAGE) from exc
        raise


def has_display_environment() -> bool:
    """Return whether the current process looks attached to a desktop display."""
    if sys.platform.startswith("win"):
        return True
    return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


def resolve_settings_path() -> Path:
    """Return the configured settings path without importing Tk-bound config models."""
    local_appdata = os.getenv("LOCALAPPDATA")
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")

    if os.name == "nt":
        base_dir = (
            Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        )
    elif sys.platform == "darwin":
        base_dir = (
            Path(xdg_config_home)
            if xdg_config_home
            else Path.home() / "Library" / "Application Support"
        )
    else:
        base_dir = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"

    default_settings_path = base_dir / "NewsNowNeon" / "ainews_settings.json"
    return Path(os.getenv("NEWS_APP_SETTINGS", str(default_settings_path)))


def is_settings_path_writable(path: Path) -> bool:
    """Return whether the configured settings path looks writable."""
    candidate_dir = path if path.is_dir() else path.parent
    existing_dir = candidate_dir if candidate_dir.exists() else candidate_dir.parent
    return os.access(existing_dir, os.W_OK)


def collect_startup_diagnostics() -> StartupDiagnostics:
    """Collect startup-readiness diagnostics without instantiating the GUI app."""
    checks: list[DiagnosticCheck] = []

    try:
        detect_tkinter_runtime()
        checks.append(
            {
                "name": "Tkinter",
                "status": "confirmed",
                "detail": "available",
                "required": True,
            }
        )
    except RuntimeError as exc:
        checks.append(
            {
                "name": "Tkinter",
                "status": "failed",
                "detail": str(exc),
                "required": True,
            }
        )

    has_display = has_display_environment()
    checks.append(
        {
            "name": "Display",
            "status": "confirmed" if has_display else "failed",
            "detail": (
                "available" if has_display else HEADLESS_DISPLAY_ERROR_MESSAGE
            ),
            "required": True,
        }
    )

    settings_path = resolve_settings_path()
    settings_writable = is_settings_path_writable(settings_path)
    checks.append(
        {
            "name": "Settings path",
            "status": "confirmed" if settings_writable else "failed",
            "detail": (
                f"writable ({settings_path})"
                if settings_writable
                else f"not writable ({settings_path})"
            ),
            "required": True,
        }
    )

    required_failures = [
        f"{check['name']}: {check['detail']}"
        for check in checks
        if check["required"] and check["status"] == "failed"
    ]

    python_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

    return {
        "python_version": python_version,
        "app_version": APP_METADATA.version,
        "checks": checks,
        "required_ready": not required_failures,
        "required_failures": required_failures,
    }


def render_startup_diagnostics(report: StartupDiagnostics) -> str:
    """Render startup diagnostics as short terminal-friendly text."""
    confirmed = [
        f"- {check['name']} {check['detail']}"
        for check in report["checks"]
        if check["status"] == "confirmed"
    ]
    failed = [
        f"- {check['name']} {check['detail']}"
        for check in report["checks"]
        if check["status"] == "failed"
    ]
    optional = [
        f"- {check['name']} {check['detail']}"
        for check in report["checks"]
        if check["status"] == "optional"
    ]

    lines = [
        f"Python: {report['python_version']}",
        f"App version: {report['app_version']}",
        "potwierdzone",
        *(confirmed or ["- none"]),
        "problem / missing prerequisite",
        *(failed or ["- none"]),
    ]

    if optional:
        lines.extend(["optional / not configured", *optional])

    verdict = "READY" if report["required_ready"] else "NOT READY"
    lines.append(f"Verdict: {verdict}")
    return "\n".join(lines)


def run_startup_diagnostics() -> str:
    """Print the startup-readiness report and exit with readiness semantics."""
    rendered = render_startup_diagnostics(collect_startup_diagnostics())
    print(rendered)
    raise SystemExit(0 if "Verdict: READY" in rendered else 1)


def bootstrap_app(settings_path: str | None = None) -> Any:
    """Create the NewsNow Neon application instance without starting mainloop."""
    app_class = load_app_class()
    app = app_class()
    if settings_path:
        load_settings_override = getattr(app, "load_settings_override", None)
        if callable(load_settings_override):
            load_settings_override(settings_path)
        else:
            logger.warning("AINewsApp has no settings override hook yet.")
    return app


def is_headless_tk_error(error: BaseException) -> bool:
    """Return whether the startup failure looks like a missing GUI display."""
    error_type_name = type(error).__name__
    if not error_type_name.endswith("TclError"):
        return False

    error_text = str(error).lower()
    return "no display name" in error_text or "no $display" in error_text


def render_startup_error(error: BaseException) -> str:
    """Return a user-facing startup error for missing Tk support or GUI display."""
    if isinstance(error, RuntimeError):
        return str(error)

    if is_headless_tk_error(error):
        return HEADLESS_DISPLAY_ERROR_MESSAGE

    return str(error)


def main(settings_path: str | None = None) -> None:
    """Launch the NewsNow Neon Tk application."""
    logger.debug("Bootstrapping NewsNow Neon main loop")

    try:
        app = bootstrap_app(settings_path=settings_path)
        app.mainloop()
    except BaseException as exc:
        if not isinstance(exc, RuntimeError) and not is_headless_tk_error(exc):
            raise
        message = render_startup_error(exc)
        print(message, file=sys.stderr)
        raise SystemExit(1) from exc


__all__ = [
    "APP_METADATA",
    "APP_VERSION",
    "HEADLESS_DISPLAY_ERROR_MESSAGE",
    "TKINTER_IMPORT_ERROR_MESSAGE",
    "StartupDiagnostics",
    "bootstrap_app",
    "collect_startup_diagnostics",
    "detect_tkinter_runtime",
    "has_display_environment",
    "is_headless_tk_error",
    "is_settings_path_writable",
    "load_app_class",
    "main",
    "render_startup_diagnostics",
    "render_startup_error",
    "resolve_settings_path",
    "run_startup_diagnostics",
]
