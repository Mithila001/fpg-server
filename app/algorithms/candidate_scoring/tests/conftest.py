from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    ScoringConfig,
    create_default_config,
    create_default_registry,
)
from app.algorithms.candidate_scoring.registry import EvaluatorRegistry

from .builders import build_scoring_input

TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / "data"


@pytest.fixture
def valid_scoring_input() -> CandidateScoringInput:
    return build_scoring_input()


@pytest.fixture
def default_registry() -> EvaluatorRegistry:
    return create_default_registry()


@pytest.fixture
def default_config() -> ScoringConfig:
    return create_default_config()


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    with (DATA_DIR / "sample_candidate.json").open(encoding="utf-8") as file:
        return json.load(file)


@pytest.fixture
def mapping_scoring_input(sample_payload: dict[str, Any]) -> CandidateScoringInput:
    return CandidateScoringInput(
        specification=sample_payload["specification"],
        candidate=sample_payload["candidate"],
    )
