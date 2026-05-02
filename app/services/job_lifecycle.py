from __future__ import annotations

import multiprocessing as mp
import queue
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.services.algorithm_manager_v2 import run_fpg_pipeline_api
from app.services.buildable_space_manager import run_buildable_space_pipeline
from app.util.room_requirements import floor_values
from app.util.unit_converter import (
    converter_cm_to_unit,
    converter_unit_to_centimeters,
    converter_unit_to_meters,
)


class JobStatus(str, Enum):
    SEARCHING = "SEARCHING"
    TERMINATED = "TERMINATED"
    TIMED_OUT = "TIMED_OUT"
    COMPLETED = "COMPLETED"


class JobKind(str, Enum):
    FORMAT_V2 = "FORMAT_V2"
    BUILDABLE_SPACE = "BUILDABLE_SPACE"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _run_format_job(request_payload: dict[str, Any]) -> dict[str, Any]:
    room_template = RoomSetupTemplateBase.model_validate(request_payload["room_template"])
    floored_width = floor_values(converter_cm_to_unit(request_payload["floor_width"]))
    floored_height = floor_values(converter_cm_to_unit(request_payload["floor_height"]))
    payload = run_fpg_pipeline_api(
        floor_width=floored_width,
        floor_height=floored_height,
        room_template=room_template,
        should_optuna_run=request_payload.get("should_optuna_run", False),
        optuna_trial_count=request_payload.get("optuna_trial_count", 20),
    )
    return converter_unit_to_centimeters(payload)


def _run_buildable_space_job(request_payload: dict[str, Any]) -> dict[str, Any]:
    land_payload = converter_cm_to_unit(
        {
            "area": request_payload["area"],
            "segmentsCoordinates": request_payload["segmentsCoordinates"],
            "roadConnected": request_payload.get("roadConnected", []),
        }
    )
    payload = run_buildable_space_pipeline(
        land_data=land_payload,
        min_width=converter_cm_to_unit(request_payload.get("min_width", 100)),
        min_height=converter_cm_to_unit(request_payload.get("min_height", 100)),
        should_plot=request_payload.get("should_plot", False),
    )
    return converter_unit_to_meters(payload)


def _worker_entry(
    job_kind: JobKind,
    request_payload: dict[str, Any],
    result_queue: mp.Queue,
) -> None:
    try:
        if job_kind == JobKind.FORMAT_V2:
            result = _run_format_job(request_payload)
        elif job_kind == JobKind.BUILDABLE_SPACE:
            result = _run_buildable_space_job(request_payload)
        else:
            raise ValueError(f"Unsupported job kind: {job_kind}")
        result_queue.put({"ok": True, "result": result})
    except Exception as exc:  # pragma: no cover - defensive fail-safe
        result_queue.put(
            {
                "ok": False,
                "result": {
                    "status": "ERROR",
                    "message": f"Job execution failed: {exc}",
                },
            }
        )


@dataclass
class _ManagedJob:
    job_id: str
    job_kind: JobKind
    client_key: str
    status: JobStatus
    pid: int
    process: mp.Process
    result_queue: mp.Queue
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    cleanup_timer: threading.Timer | None = None


class InMemoryJobRegistry:
    def __init__(
        self,
        timeout_seconds: int = settings.FPG_GENERATION_API_TIMEOUT,
        cleanup_delay_seconds: int = settings.JOB_REGISTRY_CLEANUP_DELAY,
    ) -> None:
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.cleanup_delay_seconds = max(1, int(cleanup_delay_seconds))
        self._lock = threading.Lock()
        self._jobs: dict[str, _ManagedJob] = {}
        self._active_by_client: dict[str, str] = {}

    def submit_job(
        self,
        job_kind: JobKind,
        client_key: str,
        request_payload: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            active_job_id = self._active_by_client.get(client_key)
            if active_job_id:
                active_job = self._jobs.get(active_job_id)
                if active_job and active_job.status == JobStatus.SEARCHING:
                    return {
                        "accepted": False,
                        "message": "Process is Already Running",
                        "job_id": active_job.job_id,
                    }
                self._active_by_client.pop(client_key, None)

            job_id = str(uuid4())
            result_queue: mp.Queue = mp.Queue()
            process = mp.Process(
                target=_worker_entry,
                args=(job_kind, request_payload, result_queue),
                daemon=True,
            )
            process.start()
            managed_job = _ManagedJob(
                job_id=job_id,
                job_kind=job_kind,
                client_key=client_key,
                status=JobStatus.SEARCHING,
                pid=process.pid or -1,
                process=process,
                result_queue=result_queue,
                events=[],
            )
            self._append_event_locked(managed_job, "JOB_STARTED", "Job accepted and running.")
            self._jobs[job_id] = managed_job
            self._active_by_client[client_key] = job_id

        monitor_thread = threading.Thread(
            target=self._monitor_completion,
            args=(job_id,),
            daemon=True,
        )
        monitor_thread.start()

        timeout_thread = threading.Thread(
            target=self._watchdog_timeout,
            args=(job_id,),
            daemon=True,
        )
        timeout_thread.start()

        return {
            "accepted": True,
            "message": "Job accepted for processing.",
            "job_id": job_id,
            "status": JobStatus.SEARCHING.value,
        }

    def cancel_job(self, client_key: str, job_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            target_job_id = job_id or self._active_by_client.get(client_key)
            if not target_job_id:
                return {"cancelled": False, "message": "No active job found."}
            managed_job = self._jobs.get(target_job_id)
            if not managed_job:
                return {"cancelled": False, "message": "Job not found."}
            if managed_job.status != JobStatus.SEARCHING:
                return {
                    "cancelled": False,
                    "message": f"Job is already {managed_job.status.value}.",
                    "job": self._serialize_job_locked(managed_job),
                }

        self._terminate_process(managed_job.process)
        self._mark_terminal_status(target_job_id, JobStatus.TERMINATED, "Job terminated by client request.")
        job_payload = self.get_job(target_job_id)
        return {
            "cancelled": True,
            "message": "Job cancelled successfully.",
            "job": job_payload,
        }

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            managed_job = self._jobs.get(job_id)
            if not managed_job:
                return None
            return self._serialize_job_locked(managed_job)

    def get_active_job_for_client(self, client_key: str) -> dict[str, Any] | None:
        with self._lock:
            job_id = self._active_by_client.get(client_key)
            if not job_id:
                return None
            managed_job = self._jobs.get(job_id)
            if not managed_job:
                return None
            return self._serialize_job_locked(managed_job)

    def _watchdog_timeout(self, job_id: str) -> None:
        timer = threading.Event()
        timer.wait(timeout=self.timeout_seconds)
        with self._lock:
            managed_job = self._jobs.get(job_id)
            if not managed_job or managed_job.status != JobStatus.SEARCHING:
                return
            process = managed_job.process
        self._terminate_process(process)
        self._mark_terminal_status(
            job_id=job_id,
            status=JobStatus.TIMED_OUT,
            event_message=f"Job exceeded timeout of {self.timeout_seconds}s and was terminated.",
        )

    def _monitor_completion(self, job_id: str) -> None:
        with self._lock:
            managed_job = self._jobs.get(job_id)
            if not managed_job:
                return
            process = managed_job.process
            result_queue = managed_job.result_queue

        process.join()

        with self._lock:
            latest_job = self._jobs.get(job_id)
            if not latest_job or latest_job.status != JobStatus.SEARCHING:
                return

        worker_payload: dict[str, Any] | None = None
        try:
            worker_payload = result_queue.get_nowait()
        except queue.Empty:
            worker_payload = None

        if worker_payload is None:
            result_data = {
                "status": "ERROR",
                "message": "Job ended without a result payload.",
            }
        else:
            result_data = worker_payload.get("result", {})

        self._mark_terminal_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            event_message="Job finished processing.",
            result=result_data,
        )

    def _mark_terminal_status(
        self,
        job_id: str,
        status: JobStatus,
        event_message: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            managed_job = self._jobs.get(job_id)
            if not managed_job:
                return
            if managed_job.status != JobStatus.SEARCHING:
                return

            managed_job.status = status
            managed_job.updated_at = _utc_now_iso()
            if result is not None:
                managed_job.result = result
            self._append_event_locked(managed_job, status.value, event_message)
            self._active_by_client.pop(managed_job.client_key, None)
            self._schedule_cleanup_locked(managed_job)

    def _schedule_cleanup_locked(self, managed_job: _ManagedJob) -> None:
        if managed_job.cleanup_timer:
            managed_job.cleanup_timer.cancel()
        cleanup_timer = threading.Timer(
            self.cleanup_delay_seconds,
            self._purge_job,
            args=(managed_job.job_id,),
        )
        cleanup_timer.daemon = True
        managed_job.cleanup_timer = cleanup_timer
        cleanup_timer.start()

    def _purge_job(self, job_id: str) -> None:
        with self._lock:
            managed_job = self._jobs.pop(job_id, None)
            if not managed_job:
                return
            if self._active_by_client.get(managed_job.client_key) == job_id:
                self._active_by_client.pop(managed_job.client_key, None)

    @staticmethod
    def _terminate_process(process: mp.Process) -> None:
        if not process.is_alive():
            return
        process.terminate()
        process.join(timeout=1)
        if process.is_alive() and hasattr(process, "kill"):
            process.kill()
            process.join(timeout=1)

    @staticmethod
    def _append_event_locked(managed_job: _ManagedJob, event: str, message: str) -> None:
        managed_job.updated_at = _utc_now_iso()
        managed_job.events.append(
            {
                "timestamp": managed_job.updated_at,
                "event": event,
                "message": message,
            }
        )

    @staticmethod
    def _serialize_job_locked(managed_job: _ManagedJob) -> dict[str, Any]:
        return {
            "job_id": managed_job.job_id,
            "job_kind": managed_job.job_kind.value,
            "client_key": managed_job.client_key,
            "pid": managed_job.pid,
            "status": managed_job.status.value,
            "created_at": managed_job.created_at,
            "updated_at": managed_job.updated_at,
            "events": list(managed_job.events),
            "result": managed_job.result,
        }


job_registry = InMemoryJobRegistry()
