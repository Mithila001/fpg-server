from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.artifacts import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactScope,
    ArtifactStorage,
    ArtifactStorageConfig,
    ArtifactWriteRequest,
    FeatureKey,
    WriteMode,
)
from app.artifacts.exceptions import ArtifactSerializationError
from app.core.execution import ExecutionContext

PNG = b"\x89PNG\r\n\x1a\nminimal-test-payload"


@pytest.fixture
def context() -> ExecutionContext:
    return (
        ExecutionContext.create_root(
            job_id="1842",
            started_at=datetime(2026, 7, 25, 18, 31, 52, 481000, tzinfo=UTC),
        )
        .for_search_trial(4)
        .for_candidate(2)
        .for_solver_run(1)
    )


def _storage(tmp_path: Path) -> ArtifactStorage:
    return ArtifactStorage(ArtifactStorageConfig(output_root=tmp_path))


def test_json_and_png_share_flow_and_semantic_identity(
    tmp_path: Path, context: ExecutionContext
) -> None:
    storage = _storage(tmp_path)
    json_ref = storage.save_json(
        ArtifactWriteRequest(
            feature=FeatureKey.FLOOR_PLAN_SOLVER,
            artifact_kind=ArtifactKind.FLOOR_PLAN_DATA,
            artifact_format=ArtifactFormat.JSON,
            artifact_scope=ArtifactScope.SOLVER_RUN,
            semantic_name="floor plan",
            execution_context=context,
            write_mode=WriteMode.REPLACE,
        ),
        {"solved": True},
    )
    png_ref = storage.save_png(
        ArtifactWriteRequest(
            feature=FeatureKey.FLOOR_PLAN_SOLVER,
            artifact_kind=ArtifactKind.VISUALIZATION,
            artifact_format=ArtifactFormat.PNG,
            artifact_scope=ArtifactScope.SOLVER_RUN,
            semantic_name="floor plan",
            execution_context=context,
            write_mode=WriteMode.REPLACE,
        ),
        PNG,
    )

    assert json_ref.path is not None and png_ref.path is not None
    assert json_ref.path.parents[2] == png_ref.path.parents[2]
    assert json_ref.path.stem == png_ref.path.stem
    assert json.loads(json_ref.path.read_text()) == {"solved": True}


def test_event_json_files_are_valid_under_concurrent_writers(
    tmp_path: Path, context: ExecutionContext
) -> None:
    storage = _storage(tmp_path)
    def write(value: int):
        request = ArtifactWriteRequest(
            feature=FeatureKey.PIPELINE,
            artifact_kind=ArtifactKind.EVENT_LOG,
            artifact_format=ArtifactFormat.JSON,
            artifact_scope=ArtifactScope.FLOW,
            semantic_name=f"event-{value:03d}",
            execution_context=context,
        )
        return storage.save_json(request, {"i": value}).path

    with ThreadPoolExecutor(max_workers=8) as executor:
        paths = list(executor.map(write, range(40)))

    assert all(path is not None for path in paths)
    records = [json.loads(path.read_text()) for path in paths if path is not None]
    assert sorted(record["i"] for record in records) == list(range(40))
    flow_root = next((tmp_path / "flows").iterdir())
    assert {item.name for item in flow_root.iterdir()} == {"json", "png"}
    assert not tuple(tmp_path.rglob("*.lock"))


def test_flow_directory_allocation_uses_readable_collision_suffix(
    tmp_path: Path,
) -> None:
    storage = _storage(tmp_path)
    started = datetime(2026, 7, 25, 18, 31, 52, 481000, tzinfo=UTC)
    first = storage.create_execution_context(job_id="job-a", started_at=started)
    second = storage.create_execution_context(job_id="job-b", started_at=started)

    assert str(first.flow_id) == "flow_20260725T183152.481Z"
    assert str(second.flow_id) == "flow_20260725T183152.481Z-02"
    roots = sorted(item.name for item in (tmp_path / "flows").iterdir())
    assert roots == [
        "20260725T183152.481Z_flow",
        "20260725T183152.481Z_flow-02",
    ]
    for root in (tmp_path / "flows").iterdir():
        assert {item.name for item in root.iterdir()} == {"json", "png"}


def test_create_does_not_overwrite_and_replace_is_atomic(
    tmp_path: Path, context: ExecutionContext
) -> None:
    storage = _storage(tmp_path)
    request = ArtifactWriteRequest(
        feature=FeatureKey.PIPELINE,
        artifact_kind=ArtifactKind.DIAGNOSTIC,
        artifact_format=ArtifactFormat.JSON,
        artifact_scope=ArtifactScope.FLOW,
        semantic_name="snapshot",
        execution_context=context,
    )
    storage.save_json(request, {"version": 1})
    with pytest.raises(FileExistsError):
        storage.save_json(request, {"version": 2})
    replacement = replace(request, write_mode=WriteMode.REPLACE)
    storage.save_json(replacement, {"version": 2})


def test_unsupported_json_value_is_rejected(
    tmp_path: Path, context: ExecutionContext
) -> None:
    request = ArtifactWriteRequest(
        feature=FeatureKey.PIPELINE,
        artifact_kind=ArtifactKind.DIAGNOSTIC,
        artifact_format=ArtifactFormat.JSON,
        artifact_scope=ArtifactScope.FLOW,
        semantic_name="bad",
        execution_context=context,
    )
    with pytest.raises(ArtifactSerializationError):
        _storage(tmp_path).save_json(request, {"value": object()})


def test_disabled_json_and_png_return_disabled_references(
    tmp_path: Path,
    context: ExecutionContext,
) -> None:
    storage = ArtifactStorage(
        ArtifactStorageConfig(
            output_root=tmp_path,
            json_artifacts_enabled=False,
            png_artifacts_enabled=False,
        )
    )
    json_reference = storage.save_json(
        ArtifactWriteRequest(
            feature=FeatureKey.PIPELINE,
            artifact_kind=ArtifactKind.DIAGNOSTIC,
            artifact_format=ArtifactFormat.JSON,
            artifact_scope=ArtifactScope.FLOW,
            semantic_name="disabled",
            execution_context=context,
        ),
        {"value": 1},
    )
    png_reference = storage.save_png(
        ArtifactWriteRequest(
            feature=FeatureKey.PIPELINE,
            artifact_kind=ArtifactKind.VISUALIZATION,
            artifact_format=ArtifactFormat.PNG,
            artifact_scope=ArtifactScope.FLOW,
            semantic_name="disabled",
            execution_context=context,
        ),
        PNG,
    )

    assert not json_reference.enabled and json_reference.path is None
    assert not png_reference.enabled and png_reference.path is None
