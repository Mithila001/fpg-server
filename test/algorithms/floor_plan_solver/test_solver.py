from __future__ import annotations

import pytest

pytest.importorskip("ortools")

from app.algorithms.floor_plan_solver import (
    FloorPlanSolveRequest,
    GenerationProfile,
    HardConstraintUse,
    RoomPlacementHint,
    SoftConstraintUse,
    generate_floor_plan,
)
from app.algorithms.floor_plan_solver.config import (
    PreparationConfig,
    SeedPolicy,
    SeedSource,
    SolverConfig,
)
from app.algorithms.types.domain import (
    ConstraintStrength,
    FloorPlanGenerationSpec,
    FloorSpec,
    MatchPolicy,
    RoomId,
    RoomRelationSpec,
    RoomSizeSpec,
    RoomSpec,
    RoomType,
)


def _room(room_id: str, room_type: RoomType, name: str) -> RoomSpec:
    return RoomSpec(
        id=RoomId(room_id),
        room_type=room_type,
        name=name,
        size=RoomSizeSpec(
            min_width=2.0,
            max_width=3.0,
            min_height=2.0,
            max_height=3.0,
            min_area=4.0,
            max_area=9.0,
        ),
    )


def _specification() -> FloorPlanGenerationSpec:
    living_id = RoomId("living")
    bedroom_id = RoomId("bedroom")
    return FloorPlanGenerationSpec(
        floor=FloorSpec(width=7.0, height=4.0),
        rooms=(
            _room(living_id, RoomType.LIVING_ROOM, "Living Room"),
            _room(bedroom_id, RoomType.BEDROOM, "Bedroom"),
        ),
        room_relations=(
            RoomRelationSpec(
                source_room_id=living_id,
                target_room_ids=(bedroom_id,),
                match_policy=MatchPolicy.AND,
                strength=ConstraintStrength.HARD,
            ),
        ),
    )


def _initial_profile() -> GenerationProfile:
    return GenerationProfile(
        name="test_initial",
        hard_constraints=(
            HardConstraintUse(
                "room_relations", {"minimum_overlap": 0.5}
            ),
        ),
        soft_constraints=(SoftConstraintUse("dead_space", weight=1),),
        solver=SolverConfig(max_time_seconds=5.0, num_search_workers=1),
        preparation=PreparationConfig(coordinate_scale=10),
        seed=SeedPolicy(source=SeedSource.CANDIDATE_HINTS),
    )


def test_generates_typed_floor_plan() -> None:
    result = generate_floor_plan(
        FloorPlanSolveRequest(
            specification=_specification(),
            profile=_initial_profile(),
            candidate_hints=(
                RoomPlacementHint(room_id=RoomId("living"), x=0.0, y=0.0),
            ),
        )
    )

    assert result.solved
    assert result.floor_plan is not None
    assert {str(room.id) for room in result.floor_plan.rooms} == {
        "living",
        "bedroom",
    }


def test_existing_floor_plan_can_seed_refinement() -> None:
    initial = generate_floor_plan(
        FloorPlanSolveRequest(
            specification=_specification(),
            profile=_initial_profile(),
        )
    )
    assert initial.floor_plan is not None

    refinement_profile = GenerationProfile(
        name="test_refinement",
        hard_constraints=(
            HardConstraintUse(
                "room_relations", {"minimum_overlap": 0.5}
            ),
        ),
        soft_constraints=(
            SoftConstraintUse("seed_stability", weight=10),
            SoftConstraintUse("dead_space", weight=1),
        ),
        solver=SolverConfig(max_time_seconds=5.0, num_search_workers=1),
        preparation=PreparationConfig(coordinate_scale=10),
        seed=SeedPolicy(
            source=SeedSource.EXISTING_FLOOR_PLAN,
            require_source=True,
            position_tolerance=0.5,
            size_tolerance=0.5,
            force_seeded_rooms_present=True,
        ),
    )

    refined = generate_floor_plan(
        FloorPlanSolveRequest(
            specification=_specification(),
            profile=refinement_profile,
            existing_floor_plan=initial.floor_plan,
        )
    )

    assert refined.solved
    assert refined.floor_plan is not None


def test_profiles_can_replace_constraint_configuration() -> None:
    profile = _initial_profile().with_soft_constraints(
        SoftConstraintUse("dead_space", weight=7)
    )
    assert profile.soft_constraints[0].weight == 7
