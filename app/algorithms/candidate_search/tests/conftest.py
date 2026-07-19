from __future__ import annotations

from pathlib import Path

import pytest

from ..models import CandidateSearchInput, CandidateSearchSettings, CandidateSearchTarget
from .builders import (
    RecordingEvaluator,
    build_candidate_search_input,
    build_candidate_settings,
    build_candidate_targets,
    build_recording_evaluator,
)


@pytest.fixture
def candidate_targets() -> tuple[CandidateSearchTarget, ...]:
    return build_candidate_targets()


@pytest.fixture
def candidate_settings() -> CandidateSearchSettings:
    return build_candidate_settings()


@pytest.fixture
def recording_evaluator() -> RecordingEvaluator:
    return build_recording_evaluator()


@pytest.fixture
def candidate_search_input(
    candidate_targets: tuple[CandidateSearchTarget, ...],
    candidate_settings: CandidateSearchSettings,
    recording_evaluator: RecordingEvaluator,
) -> CandidateSearchInput:
    return build_candidate_search_input(
        targets=candidate_targets,
        settings=candidate_settings,
        evaluator=recording_evaluator,
    )


@pytest.fixture
def temporary_output_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "candidate_search_output"
    output_dir.mkdir()
    return output_dir
