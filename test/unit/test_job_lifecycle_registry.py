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


def _stub_worker(_kind, _payload, result_queue):
    result_queue.put({"ok": True, "result": {"status": "OK", "message": "done"}})


def test_registry_job_completion_and_cleanup():
    _FakeProcess.behavior = "complete"
    with patch("app.services.job_lifecycle.mp.Process", _FakeProcess), patch(
        "app.services.job_lifecycle.mp.Queue", _FakeQueue
    ), patch("app.services.job_lifecycle._worker_entry", _stub_worker):
        registry = InMemoryJobRegistry(timeout_seconds=1, cleanup_delay_seconds=1)
        submit = registry.submit_job(JobKind.FORMAT_V2, "client-A", {"a": 1})
        assert submit["accepted"] is True
        job_id = submit["job_id"]

        time.sleep(0.2)
        job = registry.get_job(job_id)
        assert job is not None
        assert job["status"] == JobStatus.COMPLETED.value
        assert job["result"]["status"] == "OK"

        time.sleep(1.2)
        assert registry.get_job(job_id) is None


def test_registry_rejects_second_active_job():
    _FakeProcess.behavior = "hang"
    with patch("app.services.job_lifecycle.mp.Process", _FakeProcess), patch(
        "app.services.job_lifecycle.mp.Queue", _FakeQueue
    ):
        registry = InMemoryJobRegistry(timeout_seconds=3, cleanup_delay_seconds=1)
        first = registry.submit_job(JobKind.FORMAT_V2, "client-lock", {"a": 1})
        second = registry.submit_job(JobKind.BUILDABLE_SPACE, "client-lock", {"a": 1})
        assert first["accepted"] is True
        assert second["accepted"] is False
        assert second["message"] == "Process is Already Running"


def test_registry_cancel_and_timeout_paths():
    _FakeProcess.behavior = "hang"
    with patch("app.services.job_lifecycle.mp.Process", _FakeProcess), patch(
        "app.services.job_lifecycle.mp.Queue", _FakeQueue
    ):
        # cancel path
        registry_cancel = InMemoryJobRegistry(timeout_seconds=3, cleanup_delay_seconds=1)
        submit_cancel = registry_cancel.submit_job(JobKind.FORMAT_V2, "client-cancel", {})
        job_id_cancel = submit_cancel["job_id"]
        cancelled = registry_cancel.cancel_job("client-cancel")
        assert cancelled["cancelled"] is True
        time.sleep(0.1)
        job_cancel = registry_cancel.get_job(job_id_cancel)
        assert job_cancel is not None
        assert job_cancel["status"] == JobStatus.TERMINATED.value

        # timeout path
        registry_timeout = InMemoryJobRegistry(timeout_seconds=1, cleanup_delay_seconds=1)
        submit_timeout = registry_timeout.submit_job(JobKind.FORMAT_V2, "client-timeout", {})
        job_id_timeout = submit_timeout["job_id"]
        time.sleep(1.3)
        job_timeout = registry_timeout.get_job(job_id_timeout)
        assert job_timeout is not None
        assert job_timeout["status"] == JobStatus.TIMED_OUT.value
