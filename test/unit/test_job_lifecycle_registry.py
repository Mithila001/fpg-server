from __future__ import annotations

import queue
import time
from collections.abc import Callable
from unittest.mock import patch

from app.services.job_lifecycle import InMemoryJobRegistry, JobKind, JobStatus


class _FakeQueue(queue.Queue):
    pass


class _FakeProcess:
    _pid_counter = 2000
    behavior = "complete"

    def __init__(self, target: Callable, args: tuple, daemon: bool = True):
        self._target = target
        self._args = args
        self.daemon = daemon
        self.pid = None
        self._alive = False

    def start(self) -> None:
        type(self)._pid_counter += 1
        self.pid = type(self)._pid_counter
        self._alive = True
        if type(self).behavior == "complete":
            self._target(*self._args)
            self._alive = False

    def is_alive(self) -> bool:
        return self._alive

    def join(self, timeout: float | None = None) -> None:
        start = time.time()
        while self._alive:
            if timeout is not None and (time.time() - start) >= timeout:
                break
            time.sleep(0.01)

    def terminate(self) -> None:
        self._alive = False

    def kill(self) -> None:
        self._alive = False


def _stub_worker(_kind, _payload, result_queue, progress_queue):
    progress_queue.put(
        {
            "event": "trial_completed",
            "message": "trial 1 complete",
            "data": {"trial_number": 1},
        }
    )
    result_queue.put({"ok": True, "result": {"status": "OK", "message": "done"}})


def test_registry_job_completion_and_cleanup():
    _FakeProcess.behavior = "complete"
    with (
        patch("app.services.job_lifecycle.mp.Process", _FakeProcess),
        patch("app.services.job_lifecycle.mp.Queue", _FakeQueue),
        patch("app.services.job_lifecycle._worker_entry", _stub_worker),
    ):
        registry = InMemoryJobRegistry(timeout_seconds=1, cleanup_delay_seconds=1)
        submit = registry.submit_job(JobKind.FORMAT_V2, "client-A", {"a": 1})
        assert submit["accepted"] is True
        job_id = submit["job_id"]

        time.sleep(0.2)
        job = registry.get_job(job_id)
        assert job is not None
        assert job["status"] == JobStatus.COMPLETED.value
        assert job["result"]["status"] == "OK"
        assert any(event["event"] == "trial_completed" for event in job["events"])

        time.sleep(1.2)
        assert registry.get_job(job_id) is None


def test_registry_rejects_second_active_job():
    _FakeProcess.behavior = "hang"
    with (
        patch("app.services.job_lifecycle.mp.Process", _FakeProcess),
        patch("app.services.job_lifecycle.mp.Queue", _FakeQueue),
    ):
        registry = InMemoryJobRegistry(timeout_seconds=3, cleanup_delay_seconds=1)
        first = registry.submit_job(JobKind.FORMAT_V2, "client-lock", {"a": 1})
        second = registry.submit_job(JobKind.BUILDABLE_SPACE, "client-lock", {"a": 1})
        assert first["accepted"] is True
        assert second["accepted"] is False
        assert second["message"] == "Process is Already Running"


def test_registry_cancel_and_timeout_paths():
    _FakeProcess.behavior = "hang"
    with (
        patch("app.services.job_lifecycle.mp.Process", _FakeProcess),
        patch("app.services.job_lifecycle.mp.Queue", _FakeQueue),
    ):
        # cancel path
        registry_cancel = InMemoryJobRegistry(
            timeout_seconds=3, cleanup_delay_seconds=1
        )
        submit_cancel = registry_cancel.submit_job(
            JobKind.FORMAT_V2, "client-cancel", {}
        )
        job_id_cancel = submit_cancel["job_id"]
        cancelled = registry_cancel.cancel_job("client-cancel")
        assert cancelled["cancelled"] is True
        time.sleep(0.1)
        job_cancel = registry_cancel.get_job(job_id_cancel)
        assert job_cancel is not None
        assert job_cancel["status"] == JobStatus.TERMINATED.value

        # timeout path
        registry_timeout = InMemoryJobRegistry(
            timeout_seconds=1, cleanup_delay_seconds=1
        )
        submit_timeout = registry_timeout.submit_job(
            JobKind.FORMAT_V2, "client-timeout", {}
        )
        job_id_timeout = submit_timeout["job_id"]
        time.sleep(1.3)
        job_timeout = registry_timeout.get_job(job_id_timeout)
        assert job_timeout is not None
        assert job_timeout["status"] == JobStatus.TIMED_OUT.value


def test_registry_timeout_with_best_candidate():
    """
    Verify that when a timeout occurs with a qualifying best candidate,
    the event stream shows the best-candidate event and the terminal event,
    and the job completes with the best result.
    """

    def _stub_worker_with_best(_kind, _payload, result_queue, progress_queue):
        # Emit a best candidate event
        progress_queue.put(
            {
                "event": "current_best_updated",
                "message": "Current best floor plan updated.",
                "data": {
                    "score": 85.0,
                    "result": {
                        "status": "COMPLETED",
                        "message": "Best candidate found",
                        "score": 85.0,
                        "union_results": {"floor_plan": []},
                    },
                },
            }
        )
        # Hang (simulate a job that times out while searching for better)
        time.sleep(10)

    _FakeProcess.behavior = "complete"
    with (
        patch(
            "app.services.job_lifecycle.mp.Process",
            _FakeProcess,
        ),
        patch("app.services.job_lifecycle.mp.Queue", _FakeQueue),
        patch(
            "app.services.job_lifecycle._worker_entry",
            _stub_worker_with_best,
        ),
    ):
        registry = InMemoryJobRegistry(timeout_seconds=1, cleanup_delay_seconds=2)
        submit = registry.submit_job(JobKind.FORMAT_V2, "client-best-timeout", {"a": 1})
        assert submit["accepted"] is True
        job_id = submit["job_id"]

        # Wait for timeout to complete (timeout_seconds + margin)
        time.sleep(1.3)
        job = registry.get_job(job_id)
        assert job is not None

        # Verify terminal status is COMPLETED since best result exists
        assert job["status"] == JobStatus.COMPLETED.value

        # Verify the best result is in the final job state
        assert job["result"] is not None
        assert job["result"]["status"] == "COMPLETED"
        assert job["result"]["score"] == 85.0

        # Verify the event stream includes the best-candidate event
        events = job["events"]
        event_types = [e["event"] for e in events]
        assert "current_best_updated" in event_types, (
            f"Expected 'current_best_updated' in events, got: {event_types}"
        )

        # Verify terminal event is present
        assert "COMPLETED" in event_types, (
            f"Expected 'COMPLETED' in events, got: {event_types}"
        )

        # Verify order: best-candidate should appear before terminal
        best_idx = next(
            i for i, e in enumerate(events) if e["event"] == "current_best_updated"
        )
        term_idx = next(i for i, e in enumerate(events) if e["event"] == "COMPLETED")
        assert best_idx < term_idx, (
            f"Best candidate event (idx {best_idx}) should appear before terminal event (idx {term_idx})"
        )


def test_registry_timeout_without_best_candidate():
    """
    Verify that when a timeout occurs with no qualifying best candidate,
    the job completes with TIMED_OUT status and a failure payload.
    """

    def _stub_worker_no_best(_kind, _payload, result_queue, progress_queue):
        # Emit progress but no best-candidate event
        progress_queue.put(
            {
                "event": "fpg_infeasible",
                "message": "Solver did not find a feasible layout.",
                "data": {"status": "INFEASIBLE"},
            }
        )
        # Don't put anything in result_queue, simulate hanging

    _FakeProcess.behavior = "hang"
    with (
        patch(
            "app.services.job_lifecycle.mp.Process",
            _FakeProcess,
        ),
        patch("app.services.job_lifecycle.mp.Queue", _FakeQueue),
        patch(
            "app.services.job_lifecycle._worker_entry",
            _stub_worker_no_best,
        ),
    ):
        registry = InMemoryJobRegistry(timeout_seconds=1, cleanup_delay_seconds=2)
        submit = registry.submit_job(
            JobKind.FORMAT_V2, "client-no-best-timeout", {"a": 1}
        )
        assert submit["accepted"] is True
        job_id = submit["job_id"]

        # Wait for timeout
        time.sleep(1.3)
        job = registry.get_job(job_id)
        assert job is not None

        # Verify terminal status is timed_out
        assert job["status"] == JobStatus.TIMED_OUT.value

        # Verify failure payload
        assert job["result"] is not None
        assert job["result"]["status"] == "NO_FLOOR_PLAN"
        assert "time_out" in job["result"]["reason"]

        # Verify terminal event is present
        events = job["events"]
        event_types = [e["event"] for e in events]
        assert "timed_out" in event_types, (
            f"Expected 'timed_out' in events, got: {event_types}"
        )
