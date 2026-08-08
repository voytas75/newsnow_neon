"""Regression coverage for auto-refresh job cancellation."""

from __future__ import annotations

from newsnow_neon.app.controller.auto_refresh_controller import AutoRefreshController


class _App:
    """Minimal scheduler owner for controller cancellation tests."""

    def __init__(self, *, fail_after_cancel: bool = False) -> None:
        self._refresh_job: str | None = "refresh-job"
        self._countdown_job: str | None = "countdown-job"
        self.cancelled_jobs: list[str] = []
        self.fail_after_cancel = fail_after_cancel

    def after_cancel(self, job: str) -> None:
        """Record a cancellation and optionally emulate an expired Tk job."""
        self.cancelled_jobs.append(job)
        if self.fail_after_cancel:
            raise RuntimeError("job already expired")


def test_cancel_pending_jobs_cancels_and_clears_both_job_ids() -> None:
    """Cancel each scheduled job and leave no stale scheduler identifier."""
    app = _App()

    AutoRefreshController(app).cancel_pending_jobs()

    assert app.cancelled_jobs == ["refresh-job", "countdown-job"]
    assert app._refresh_job is None
    assert app._countdown_job is None


def test_cancel_pending_jobs_clears_job_ids_after_scheduler_errors() -> None:
    """Expired Tk jobs must not leave retryable stale identifiers behind."""
    app = _App(fail_after_cancel=True)

    AutoRefreshController(app).cancel_pending_jobs()

    assert app.cancelled_jobs == ["refresh-job", "countdown-job"]
    assert app._refresh_job is None
    assert app._countdown_job is None
