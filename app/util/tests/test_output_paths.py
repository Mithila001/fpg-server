from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.util.output_paths import (
    create_artifact_path,
    create_run_directory,
    get_output_root,
    safe_path_component,
    utc_timestamp,
)


def test_output_root_defaults_to_project_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OUTPUT_ROOT", raising=False)

    assert get_output_root().name == "output"
    assert get_output_root().parent.name == "fpg-server"


def test_output_root_honors_environment_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configured = tmp_path / "managed-artifacts"
    monkeypatch.setenv("OUTPUT_ROOT", str(configured))

    assert get_output_root() == configured.resolve()


def test_timestamp_is_sortable_utc_with_microseconds() -> None:
    value = datetime(2026, 7, 22, 6, 15, 30, 123456, tzinfo=UTC)

    assert utc_timestamp(value) == "20260722T061530123456Z"


def test_run_directory_and_artifact_follow_managed_templates(
    tmp_path: Path,
) -> None:
    timestamp = "20260722T061530123456Z"
    directory = create_run_directory(
        "json",
        "Candidate Search",
        "request/42",
        run_timestamp=timestamp,
        output_root=tmp_path,
    )
    artifact = create_artifact_path(
        directory,
        "best candidate",
        ".json",
        timestamp=timestamp,
        unique_id="abc12345",
    )

    assert directory == (
        tmp_path
        / "json"
        / "Candidate_Search"
        / "20260722T061530123456Z_request_42"
    )
    assert directory.is_dir()
    assert artifact.name == (
        "20260722T061530123456Z_best_candidate_abc12345.json"
    )


def test_artifact_paths_are_collision_resistant(tmp_path: Path) -> None:
    first = create_artifact_path(tmp_path, "result", "json")
    second = create_artifact_path(tmp_path, "result", "json")

    assert first != second


@pytest.mark.parametrize("value", ["", "...", "///"])
def test_empty_sanitized_components_are_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        safe_path_component(value)
