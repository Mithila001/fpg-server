from __future__ import annotations

from pathlib import Path

import pytest

from app.algorithms.types_new import FloorPlan, FloorPlanGenerationSpec

from .builders import build_floor_plan, build_generation_spec


@pytest.fixture
def realistic_floor_plan() -> FloorPlan:
    return build_floor_plan()


@pytest.fixture
def realistic_specification() -> FloorPlanGenerationSpec:
    return build_generation_spec()


@pytest.fixture
def realistic_case(
    realistic_floor_plan: FloorPlan,
    realistic_specification: FloorPlanGenerationSpec,
) -> tuple[FloorPlan, FloorPlanGenerationSpec]:
    return realistic_floor_plan, realistic_specification


@pytest.fixture
def debug_output_dir() -> Path:
    return Path(__file__).resolve().parent / "output"
