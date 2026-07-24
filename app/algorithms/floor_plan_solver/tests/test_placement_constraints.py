from __future__ import annotations

from dataclasses import replace

import pytest

from app.algorithms.floor_plan_solver import (
    FloorPlanSolveRequest,
    FloorPlanSolver,
    GenerationProfile,
    HardConstraintUse,
    INITIAL_GENERATION_PROFILE,
    RoomPlacementHint,
    SoftConstraintUse,
    SolverStatus,
)
from app.algorithms.floor_plan_solver.config import (
    PreparationConfig,
    SeedPolicy,
    SeedSource,
    SolverConfig,
)
from app.algorithms.types_new import (
    FloorPlanGenerationSpec,
    FloorSpec,
    RoomId,
    RoomSizeSpec,
    RoomSpec,
    RoomType,
)

from .assertions import rectangle_bounds


def _room(
    room_id: str,
    room_type: RoomType,
    *,
    min_width: float = 5,
    max_width: float = 10,
    min_area: float = 25,
    max_area: float = 100,
) -> RoomSpec:
    return RoomSpec(
        id=RoomId(room_id),
        room_type=room_type,
        name=room_id.replace("_", " ").title(),
        size=RoomSizeSpec(
            min_width=min_width,
            max_width=max_width,
            min_area=min_area,
            max_area=max_area,
        ),
    )


def _profile(
    *,
    hard: tuple[HardConstraintUse, ...] = (),
    soft: tuple[SoftConstraintUse, ...] = (),
    fixed_seed: bool = False,
) -> GenerationProfile:
    return GenerationProfile(
        name="focused_constraint_test",
        hard_constraints=hard,
        soft_constraints=soft,
        solver=SolverConfig(
            max_time_seconds=2,
            num_search_workers=1,
            random_seed=7,
        ),
        preparation=PreparationConfig(coordinate_scale=1),
        seed=SeedPolicy(
            source=SeedSource.CANDIDATE_HINTS if fixed_seed else SeedSource.NONE,
            require_source=fixed_seed,
            apply_hints=True,
            position_tolerance=0 if fixed_seed else None,
            size_tolerance=0 if fixed_seed else None,
            force_seeded_rooms_present=fixed_seed,
        ),
    )


def _solve(
    rooms: tuple[RoomSpec, ...],
    profile: GenerationProfile,
    *,
    floor_width: float = 30,
    floor_length: float = 30,
    hints: tuple[RoomPlacementHint, ...] = (),
):
    specification = FloorPlanGenerationSpec(
        floor=FloorSpec(width=floor_width, length=floor_length),
        rooms=rooms,
        room_relations=(),
    )
    return FloorPlanSolver().solve(
        FloorPlanSolveRequest(
            specification=specification,
            profile=profile,
            candidate_hints=hints,
        )
    )


@pytest.mark.parametrize(("width", "length"), ((10, 12), (12, 10)))
def test_shorter_side_width_range_supports_both_orientations(
    width: int,
    length: int,
) -> None:
    room = _room(
        "bedroom",
        RoomType.BEDROOM,
        min_width=5,
        max_width=10,
        min_area=120,
        max_area=120,
    )
    result = _solve(
        (room,),
        _profile(fixed_seed=True),
        hints=(
            RoomPlacementHint(
                room_id=room.id,
                x=5,
                y=5,
                width=width,
                length=length,
            ),
        ),
    )

    assert result.solved
    assert result.floor_plan is not None
    bounds = rectangle_bounds(result.floor_plan.rooms[0].boundary)
    assert (bounds.width, bounds.length) == pytest.approx((width, length))
    assert min(bounds.width, bounds.length) == pytest.approx(10)
    assert max(bounds.width, bounds.length) > room.size.max_width


def test_front_anchor_allows_empty_front_strip_and_forbids_disallowed_tie() -> None:
    living = _room("living", RoomType.LIVING_ROOM)
    kitchen = _room("kitchen", RoomType.KITCHEN)
    profile = _profile(
        hard=(
            HardConstraintUse(
                "front_anchor",
                {
                    "anchor_room_types": (
                        RoomType.VERANDA,
                        RoomType.LIVING_ROOM,
                        RoomType.BEDROOM,
                    )
                },
            ),
        ),
        fixed_seed=True,
    )

    valid = _solve(
        (living, kitchen),
        profile,
        hints=(
            RoomPlacementHint(living.id, 0, 5, 5, 5),
            RoomPlacementHint(kitchen.id, 10, 6, 5, 5),
        ),
    )
    tied = _solve(
        (living, kitchen),
        profile,
        hints=(
            RoomPlacementHint(living.id, 0, 5, 5, 5),
            RoomPlacementHint(kitchen.id, 10, 5, 5, 5),
        ),
    )

    assert valid.solved
    assert tied.status is SolverStatus.INFEASIBLE


def test_front_anchor_requires_an_allowed_room_type() -> None:
    result = _solve(
        (_room("kitchen", RoomType.KITCHEN),),
        _profile(hard=(HardConstraintUse("front_anchor"),)),
    )

    assert result.status is SolverStatus.INFEASIBLE


def test_front_anchor_allows_multiple_allowed_types_to_tie() -> None:
    living = _room("living", RoomType.LIVING_ROOM)
    bedroom = _room("bedroom", RoomType.BEDROOM)
    kitchen = _room("kitchen", RoomType.KITCHEN)
    result = _solve(
        (living, bedroom, kitchen),
        _profile(
            hard=(HardConstraintUse("front_anchor"),),
            fixed_seed=True,
        ),
        hints=(
            RoomPlacementHint(living.id, 0, 5, 5, 5),
            RoomPlacementHint(bedroom.id, 10, 5, 5, 5),
            RoomPlacementHint(kitchen.id, 20, 6, 5, 5),
        ),
    )

    assert result.solved


def test_garage_placement_forces_a_front_corner() -> None:
    living = _room("living", RoomType.LIVING_ROOM)
    garage = _room("garage", RoomType.GARAGE)
    result = _solve(
        (living, garage),
        _profile(
            hard=(
                HardConstraintUse("front_anchor"),
                HardConstraintUse("garage_placement"),
            ),
        ),
    )

    assert result.solved
    assert result.floor_plan is not None
    rooms = {
        str(room.id): rectangle_bounds(room.boundary)
        for room in result.floor_plan.rooms
    }
    assert rooms["garage"].min_y == pytest.approx(0)
    assert rooms["garage"].min_x == pytest.approx(0) or rooms[
        "garage"
    ].max_x == pytest.approx(30)


def test_veranda_is_forced_to_the_front_boundary() -> None:
    veranda = _room("veranda", RoomType.VERANDA)
    living = _room("living", RoomType.LIVING_ROOM)
    result = _solve(
        (veranda, living),
        _profile(
            hard=(
                HardConstraintUse("front_anchor"),
                HardConstraintUse(
                    "boundary_placement",
                    {
                        "rules": (
                            {
                                "room_types": (RoomType.VERANDA,),
                                "side": "front",
                            },
                        )
                    },
                ),
            ),
        ),
    )

    assert result.solved
    assert result.floor_plan is not None
    veranda_result = next(
        room for room in result.floor_plan.rooms if room.room_type is RoomType.VERANDA
    )
    assert rectangle_bounds(veranda_result.boundary).min_y == pytest.approx(0)


def test_default_profile_requires_garage_depth_to_exceed_width() -> None:
    garage_override = next(
        use
        for use in INITIAL_GENERATION_PROFILE.hard_constraints
        if use.key == "aspect_ratio"
    ).settings["overrides"][RoomType.GARAGE]

    assert garage_override["max_ratio"] < 1


@pytest.mark.parametrize(
    ("room_type", "exposed_width"),
    (
        (RoomType.KITCHEN, 10),
        (RoomType.KITCHEN, 12),
        (RoomType.HALLWAY, 10),
    ),
)
def test_back_exposure_accepts_kitchen_or_hallway(
    room_type: RoomType,
    exposed_width: int,
) -> None:
    room = _room(
        room_type.value,
        room_type,
        min_width=10,
        max_width=10,
        min_area=exposed_width * 10,
        max_area=exposed_width * 10,
    )
    result = _solve(
        (room,),
        _profile(
            hard=(HardConstraintUse("back_exposure"),),
            fixed_seed=True,
        ),
        hints=(RoomPlacementHint(room.id, 0, 20, exposed_width, 10),),
    )

    assert result.solved


def test_back_exposure_rejects_short_or_non_boundary_wall() -> None:
    short = _room(
        "kitchen",
        RoomType.KITCHEN,
        min_width=9,
        max_width=9,
        min_area=81,
        max_area=81,
    )
    short_result = _solve(
        (short,),
        _profile(
            hard=(HardConstraintUse("back_exposure"),),
            fixed_seed=True,
        ),
        hints=(RoomPlacementHint(short.id, 0, 21, 9, 9),),
    )

    kitchen = _room(
        "wide_kitchen",
        RoomType.KITCHEN,
        min_width=10,
        max_width=10,
        min_area=100,
        max_area=100,
    )
    away_from_back = _solve(
        (kitchen,),
        _profile(
            hard=(HardConstraintUse("back_exposure"),),
            fixed_seed=True,
        ),
        hints=(RoomPlacementHint(kitchen.id, 0, 19, 10, 10),),
    )

    assert short_result.status is SolverStatus.INFEASIBLE
    assert away_from_back.status is SolverStatus.INFEASIBLE


def test_back_exposure_requires_an_eligible_room_type() -> None:
    result = _solve(
        (_room("bathroom", RoomType.BATHROOM),),
        _profile(hard=(HardConstraintUse("back_exposure"),)),
    )

    assert result.status is SolverStatus.INFEASIBLE


def test_kitchen_back_preference_selects_kitchen_when_feasible() -> None:
    kitchen = _room(
        "kitchen",
        RoomType.KITCHEN,
        min_width=10,
        max_width=10,
        min_area=100,
        max_area=100,
    )
    hallway = replace(kitchen, id=RoomId("hallway"), room_type=RoomType.HALLWAY)
    result = _solve(
        (kitchen, hallway),
        _profile(
            hard=(HardConstraintUse("back_exposure"),),
            soft=(SoftConstraintUse("kitchen_back_exposure", weight=10),),
        ),
        floor_width=20,
        floor_length=20,
    )

    assert result.solved
    assert result.floor_plan is not None
    rooms = {
        str(room.id): rectangle_bounds(room.boundary)
        for room in result.floor_plan.rooms
    }
    assert rooms["kitchen"].max_y == pytest.approx(20)


def test_kitchen_back_preference_uses_hallway_when_kitchen_is_forced_front() -> None:
    kitchen = _room(
        "kitchen",
        RoomType.KITCHEN,
        min_width=10,
        max_width=10,
        min_area=100,
        max_area=100,
    )
    hallway = replace(kitchen, id=RoomId("hallway"), room_type=RoomType.HALLWAY)
    profile = _profile(
        hard=(
            HardConstraintUse("back_exposure"),
            HardConstraintUse(
                "boundary_placement",
                {
                    "rules": (
                        {
                            "room_types": (RoomType.KITCHEN,),
                            "side": "front",
                        },
                    )
                },
            ),
        ),
        soft=(SoftConstraintUse("kitchen_back_exposure", weight=10),),
    )
    result = _solve(
        (kitchen, hallway),
        profile,
        floor_width=20,
        floor_length=20,
    )

    assert result.solved
    assert result.floor_plan is not None
    rooms = {str(room.id): rectangle_bounds(room.boundary) for room in result.floor_plan.rooms}
    assert rooms["kitchen"].min_y == pytest.approx(0)
    assert rooms["hallway"].max_y == pytest.approx(20)
