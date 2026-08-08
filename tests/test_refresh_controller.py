"""Regression coverage for the explicit manual refresh trigger."""

from __future__ import annotations

from types import SimpleNamespace

from newsnow_neon.app.controller import refresh_controller


class _NextRefreshVar:
    """Capture the next-refresh label supplied by the controller."""

    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        """Store the assigned value."""
        self.value = value


def test_refresh_exits_history_updates_status_and_starts_daemon_worker(
    monkeypatch,
) -> None:
    """Manual refresh preserves the UI transition before background work starts."""
    events: list[object] = []
    next_refresh_var = _NextRefreshVar()
    app = SimpleNamespace(
        _history_mode=True,
        next_refresh_var=next_refresh_var,
        _exit_history_mode=lambda **kwargs: events.append(("exit_history", kwargs)),
        _log_status=lambda message: events.append(("status", message)),
        _update_status_summary=lambda: events.append("summary"),
        _refresh_worker=lambda force_refresh: events.append(("worker", force_refresh)),
    )
    created_threads: list[_FakeThread] = []

    class _FakeThread:
        def __init__(self, *, target, args, daemon: bool) -> None:
            self.target = target
            self.args = args
            self.daemon = daemon
            self.started = False
            created_threads.append(self)

        def start(self) -> None:
            self.started = True

    monkeypatch.setattr(refresh_controller.threading, "Thread", _FakeThread)

    refresh_controller.RefreshController(app).refresh(force_refresh=True)

    assert events == [
        ("exit_history", {"trigger_refresh": False}),
        ("status", "Fetching AI headlines…"),
        "summary",
    ]
    assert next_refresh_var.value == "Refreshing…"
    assert len(created_threads) == 1
    worker = created_threads[0]
    assert worker.target is app._refresh_worker
    assert worker.args == (True,)
    assert worker.daemon is True
    assert worker.started is True
