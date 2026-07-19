from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from app.algorithms.floor_plan_solver import (
    FloorPlanSolveRequest,
    GenerationProfile,
    INITIAL_GENERATION_PROFILE,
    REFINEMENT_A_PROFILE,
    REFINEMENT_B_PROFILE,
    RoomPlacementHint,
)
from app.algorithms.types_new.floor_plan import FloorPlan
from app.algorithms.types_new.floor_plan_spec import (
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

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_SCENARIO_PATH = DATA_DIR / "realistic_family_house.json"
UNITS_PER_METER = 10
UNIT_SIZE_CENTIMETERS = 10


def load_scenario_data(path: Path = DEFAULT_SCENARIO_PATH) -> dict[str, Any]:
    """Load reusable realistic test data without executing the solver."""

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    measurement = data.get("measurement", {})
    if measurement.get("units_per_meter") != UNITS_PER_METER:
        raise ValueError(
            f"Scenario must use {UNITS_PER_METER} project units per meter"
        )
    if measurement.get("unit_size_centimeters") != UNIT_SIZE_CENTIMETERS:
        raise ValueError(
            f"Scenario project unit must equal {UNIT_SIZE_CENTIMETERS} cm"
        )
    return data


def _build_room_spec(data: dict[str, Any]) -> RoomSpec:
    size = data["size"]
    return RoomSpec(
        id=RoomId(data["id"]),
        room_type=RoomType(data["room_type"]),
        name=data["name"],
        size=RoomSizeSpec(
            min_width=size["min_width"],
            max_width=size["max_width"],
            min_height=size["min_height"],
            max_height=size["max_height"],
            min_area=size["min_area"],
            max_area=size["max_area"],
        ),
        required=data.get("required", True),
    )


def _build_relation_spec(data: dict[str, Any]) -> RoomRelationSpec:
    return RoomRelationSpec(
        source_room_id=RoomId(data["source_room_id"]),
        target_room_ids=tuple(RoomId(value) for value in data["target_room_ids"]),
        match_policy=MatchPolicy(data["match_policy"]),
        strength=ConstraintStrength(data["strength"]),
    )


def build_realistic_generation_spec(
    *,
    floor_width: int | None = None,
    floor_height: int | None = None,
) -> FloorPlanGenerationSpec:
    """Build the realistic family-house specification used by integration tests.

    All length values are whole project units. Ten units equal one meter.
    """

    data = load_scenario_data()
    floor = data["floor"]
    return FloorPlanGenerationSpec(
        floor=FloorSpec(
            width=floor_width if floor_width is not None else floor["width"],
            height=floor_height if floor_height is not None else floor["height"],
        ),
        rooms=tuple(_build_room_spec(room) for room in data["rooms"]),
        room_relations=tuple(
            _build_relation_spec(relation) for relation in data["room_relations"]
        ),
    )


def build_realistic_candidate_hints() -> tuple[RoomPlacementHint, ...]:
    data = load_scenario_data()
    return tuple(
        RoomPlacementHint(
            room_id=RoomId(hint["room_id"]),
            x=hint["x"],
            y=hint["y"],
            width=hint.get("width"),
            height=hint.get("height"),
        )
        for hint in data["candidate_hints"]
    )


def build_solver_request(
    *,
    profile: GenerationProfile = INITIAL_GENERATION_PROFILE,
    specification: FloorPlanGenerationSpec | None = None,
    candidate_hints: tuple[RoomPlacementHint, ...] | None = None,
    existing_floor_plan: FloorPlan | None = None,
) -> FloorPlanSolveRequest:
    """Build a valid default request while allowing focused overrides."""

    return FloorPlanSolveRequest(
        specification=specification or build_realistic_generation_spec(),
        profile=profile,
        candidate_hints=(
            build_realistic_candidate_hints()
            if candidate_hints is None and profile.name == "initial_generation"
            else candidate_hints or ()
        ),
        existing_floor_plan=existing_floor_plan,
    )


def build_integration_profile(
    profile: GenerationProfile,
    *,
    max_time_seconds: float,
    random_seed: int = 20260719,
) -> GenerationProfile:
    """Keep profile behavior intact while making test runtime deterministic.

    Only OR-Tools runtime controls are changed. Constraint selection, weights,
    seed policy, and preparation settings remain the production profile values.
    """

    solver = replace(
        profile.solver,
        max_time_seconds=max_time_seconds,
        num_search_workers=1,
        random_seed=random_seed,
        log_search_progress=False,
    )
    return replace(profile, solver=solver)


def build_initial_integration_profile() -> GenerationProfile:
    return build_integration_profile(
        INITIAL_GENERATION_PROFILE,
        max_time_seconds=5.0,
    )


def build_refinement_a_integration_profile() -> GenerationProfile:
    return build_integration_profile(
        REFINEMENT_A_PROFILE,
        max_time_seconds=3.0,
    )


def build_refinement_b_integration_profile() -> GenerationProfile:
    return build_integration_profile(
        REFINEMENT_B_PROFILE,
        max_time_seconds=3.0,
    )


def build_infeasible_generation_spec() -> FloorPlanGenerationSpec:
    """Create a valid but geometrically impossible real CP-SAT problem."""

    fixed_room_size = RoomSizeSpec(
        min_width=30,
        max_width=30,
        min_height=30,
        max_height=30,
        min_area=900,
        max_area=900,
    )
    return FloorPlanGenerationSpec(
        floor=FloorSpec(width=40, height=40),
        rooms=(
            RoomSpec(
                id=RoomId("large_room_a"),
                room_type=RoomType.BEDROOM,
                name="Large Room A",
                size=fixed_room_size,
            ),
            RoomSpec(
                id=RoomId("large_room_b"),
                room_type=RoomType.BEDROOM,
                name="Large Room B",
                size=fixed_room_size,
            ),
        ),
        room_relations=(),
    )
