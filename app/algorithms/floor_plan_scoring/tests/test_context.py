from __future__ import annotations

import pytest

from app.algorithms.floor_plan_scoring import ScoringContextFactory
from app.algorithms.floor_plan_scoring.context import shared_boundary_length
from app.algorithms.types_new import FloorPlan, FloorPlanGenerationSpec

from .builders import load_case_data


def test_realistic_case_uses_project_measurement_convention(
    realistic_case: tuple[FloorPlan, FloorPlanGenerationSpec],
) -> None:
    floor_plan, specification = realistic_case
    data = load_case_data()

    assert data["measurement"]["units_per_meter"] == 10
    assert specification.floor.width == 120
    assert specification.floor.length == 100

    context = ScoringContextFactory().build(floor_plan, specification)
    living_room = context.rooms_by_id["living_1"]

    # 50 x 40 units = 5 m x 4 m = 20 square meters.
    assert living_room.area == pytest.approx(2000.0)
    assert living_room.area / 100.0 == pytest.approx(20.0)
    assert all(
        coordinate.is_integer()
        for room in context.rooms
        for point in room.points
        for coordinate in point
    )


def test_context_builds_real_room_geometry_and_adjacency_cache(
    realistic_case: tuple[FloorPlan, FloorPlanGenerationSpec],
) -> None:
    floor_plan, specification = realistic_case

    context = ScoringContextFactory().build(floor_plan, specification)

    assert len(context.rooms) == 8
    assert context.room_union is not None
    assert context.room_union.area == pytest.approx(10200.0)
    assert context.geometry_build_error is None
    assert shared_boundary_length(context, "living_1", "dining_1") == pytest.approx(
        40.0
    )
    assert shared_boundary_length(context, "dining_1", "kitchen_1") == pytest.approx(
        40.0
    )
    assert shared_boundary_length(context, "hallway_1", "bathroom_1") == pytest.approx(
        20.0
    )
