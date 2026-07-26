from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from itertools import count
from pathlib import Path
from threading import Lock, get_ident
from typing import Any

from app.core.execution import ExecutionContext, flow_directory_name

from .config import ArtifactStorageConfig
from .enums import ArtifactFormat, ArtifactKind, ArtifactScope, WriteMode
from .exceptions import ArtifactWriteError
from .models import ArtifactReference, ArtifactWriteRequest
from .paths import resolve_artifact_path
from .serializers import to_json_value

_temporary_counter = count(1)
_temporary_counter_lock = Lock()


class ArtifactStorage:
    def __init__(self, config: ArtifactStorageConfig | None = None) -> None:
        self.config = config or ArtifactStorageConfig.from_environment()

    def save_json(
        self, request: ArtifactWriteRequest, data: Any
    ) -> ArtifactReference:
        self._require(
            request,
            ArtifactFormat.JSON,
            {WriteMode.CREATE, WriteMode.REPLACE},
        )
        if request.artifact_kind is ArtifactKind.EVENT_LOG:
            enabled = (
                self.config.application_logging_enabled
                if request.artifact_scope is ArtifactScope.GLOBAL
                else self.config.flow_logging_enabled
            )
            if not enabled:
                return self._disabled_reference(request)
        elif not self.config.json_artifacts_enabled:
            return self._disabled_reference(request)
        encoded = (
            json.dumps(
                to_json_value(data),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        return self._write_snapshot(request, encoded)

    def save_png(
        self, request: ArtifactWriteRequest, png_bytes: bytes
    ) -> ArtifactReference:
        self._require(
            request,
            ArtifactFormat.PNG,
            {WriteMode.CREATE, WriteMode.REPLACE},
        )
        if not self.config.png_artifacts_enabled:
            return self._disabled_reference(request)
        if not isinstance(png_bytes, bytes) or not png_bytes.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            raise ArtifactWriteError("save_png requires valid PNG bytes")
        return self._write_snapshot(request, png_bytes)

    def create_execution_context(
        self,
        *,
        job_id: str | None = None,
        started_at: datetime | None = None,
        seed: int | None = None,
    ) -> ExecutionContext:
        """Atomically reserve one readable flow directory and its identity."""

        current = started_at or datetime.now(UTC)
        sequence = 1
        while True:
            context = ExecutionContext.create_root(
                job_id=job_id,
                started_at=current,
                seed=seed,
                flow_sequence=sequence,
            )
            flow_root = self.config.output_root / "flows" / flow_directory_name(
                started_at=context.flow_started_at,
                flow_id=str(context.flow_id),
            )
            try:
                flow_root.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                sequence += 1
                continue
            (flow_root / "json").mkdir()
            (flow_root / "png").mkdir()
            return context

    def _write_snapshot(
        self, request: ArtifactWriteRequest, content: bytes
    ) -> ArtifactReference:
        path = resolve_artifact_path(self.config, request)
        if request.artifact_scope is not ArtifactScope.GLOBAL:
            context = request.execution_context
            assert context is not None
            flow_root = self.config.output_root / "flows" / flow_directory_name(
                started_at=context.flow_started_at,
                flow_id=str(context.flow_id),
            )
            flow_root.mkdir(parents=True, exist_ok=True)
            (flow_root / "json").mkdir(exist_ok=True)
            (flow_root / "png").mkdir(exist_ok=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.config.atomic_writes_enabled:
            with _temporary_counter_lock:
                sequence = next(_temporary_counter)
            temporary = path.with_name(
                f".{path.name}.p{os.getpid()}t{get_ident()}c{sequence}.tmp"
            )
            try:
                temporary.write_bytes(content)
                if request.write_mode is WriteMode.CREATE:
                    os.link(temporary, path)
                    temporary.unlink()
                else:
                    os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()
        else:
            if request.write_mode is WriteMode.CREATE:
                with path.open("xb") as stream:
                    stream.write(content)
            else:
                path.write_bytes(content)
        return self._reference(path, request)

    @staticmethod
    def _require(
        request: ArtifactWriteRequest,
        expected_format: ArtifactFormat,
        write_modes: set[WriteMode],
    ) -> None:
        if request.artifact_format is not expected_format:
            raise ArtifactWriteError(
                f"operation requires {expected_format.value} artifact format"
            )
        if request.write_mode not in write_modes:
            raise ArtifactWriteError(
                f"unsupported {request.write_mode.value} mode "
                f"for {expected_format.value}"
            )

    def _reference(
        self, path: Path, request: ArtifactWriteRequest
    ) -> ArtifactReference:
        resolved = path.resolve()
        return ArtifactReference(
            path=resolved,
            relative_path=resolved.relative_to(
                self.config.output_root.resolve()
            ).as_posix(),
            artifact_format=request.artifact_format,
            artifact_kind=request.artifact_kind,
        )

    @staticmethod
    def _disabled_reference(request: ArtifactWriteRequest) -> ArtifactReference:
        return ArtifactReference(
            path=None,
            relative_path=None,
            artifact_format=request.artifact_format,
            artifact_kind=request.artifact_kind,
            enabled=False,
        )


def get_artifact_storage() -> ArtifactStorage:
    return ArtifactStorage()
