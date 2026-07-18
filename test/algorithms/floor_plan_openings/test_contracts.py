from __future__ import annotations

import pytest
from ortools.sat.python import cp_model

from app.algorithms.floor_plan_openings.exceptions import OpeningConfigurationError
from app.algorithms.floor_plan_openings.features.interior_doors import InteriorDoorFeature
from app.algorithms.floor_plan_openings.registry import OpeningFeatureRegistry
from app.algorithms.floor_plan_openings.runner import _map_status
from app.algorithms.floor_plan_openings.contracts import OpeningGenerationStatus


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (cp_model.OPTIMAL, OpeningGenerationStatus.OPTIMAL),
        (cp_model.FEASIBLE, OpeningGenerationStatus.FEASIBLE),
        (cp_model.INFEASIBLE, OpeningGenerationStatus.INFEASIBLE),
        (cp_model.MODEL_INVALID, OpeningGenerationStatus.MODEL_INVALID),
        (cp_model.UNKNOWN, OpeningGenerationStatus.UNKNOWN),
    ],
)
def test_solver_status_mapping(raw: int, expected: OpeningGenerationStatus) -> None:
    assert _map_status(raw) is expected


def test_registry_rejects_duplicate_feature_ids() -> None:
    registry = OpeningFeatureRegistry()
    registry.register(InteriorDoorFeature())
    with pytest.raises(OpeningConfigurationError):
        registry.register(InteriorDoorFeature())
