# test/algorithms/candidate_scoring/run_candidate_scoring.py

"""Run the real candidate-scoring component with realistic mock input.

Run this file from the fpg-server repository root:
    python test/algorithms/candidate_scoring/run_candidate_scoring.py
"""

from __future__ import annotations

import random

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    ScoringResult,
    create_default_config,
    create_default_registry,
    evaluate_candidate,
)
from app.algorithms.candidate_search import CandidatePoint
from app.algorithms.types_new import (
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

TRIAL_COUNT = 20
RANDOM_SEED = 42
GRID_RESOLUTION = 1.0


def room(
    room_id: str,
    room_type: RoomType,
    name: str,
    *,
    min_width: float,
    max_width: float,
    min_height: float,
    max_height: float,
    min_area: float,
    max_area: float,
) -> RoomSpec:
    return RoomSpec(
        id=RoomId(room_id),
        room_type=room_type,
        name=name,
        size=RoomSizeSpec(
            min_width=min_width,
            max_width=max_width,
            min_height=min_height,
            max_height=max_height,
            min_area=min_area,
            max_area=max_area,
        ),
    )


def build_mock_specification() -> FloorPlanGenerationSpec:
    """A realistic small residential floor-plan request."""
    rooms = (
        room(
            "veranda_1",
            RoomType.VERANDA,
            "Veranda",
            min_width=3.0,
            max_width=8.0,
            min_height=2.0,
            max_height=4.0,
            min_area=6.0,
            max_area=24.0,
        ),
        room(
            "garage_1",
            RoomType.GARAGE,
            "Garage",
            min_width=3.0,
            max_width=6.0,
            min_height=5.0,
            max_height=8.0,
            min_area=15.0,
            max_area=40.0,
        ),
        room(
            "living_room_1",
            RoomType.LIVING_ROOM,
            "Living Room",
            min_width=4.0,
            max_width=8.0,
            min_height=4.0,
            max_height=7.0,
            min_area=20.0,
            max_area=42.0,
        ),
        room(
            "kitchen_1",
            RoomType.KITCHEN,
            "Kitchen",
            min_width=3.0,
            max_width=5.0,
            min_height=3.0,
            max_height=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "dining_room_1",
            RoomType.DINING_ROOM,
            "Dining Room",
            min_width=3.0,
            max_width=5.0,
            min_height=3.0,
            max_height=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "hallway_1",
            RoomType.HALLWAY,
            "Hallway",
            min_width=1.0,
            max_width=2.5,
            min_height=4.0,
            max_height=12.0,
            min_area=5.0,
            max_area=20.0,
        ),
        room(
            "bedroom_1",
            RoomType.BEDROOM,
            "Bedroom 1",
            min_width=3.0,
            max_width=5.0,
            min_height=3.0,
            max_height=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "bedroom_2",
            RoomType.BEDROOM,
            "Bedroom 2",
            min_width=3.0,
            max_width=5.0,
            min_height=3.0,
            max_height=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "bathroom_1",
            RoomType.BATHROOM,
            "Bathroom",
            min_width=2.0,
            max_width=4.0,
            min_height=2.0,
            max_height=4.0,
            min_area=4.0,
            max_area=12.0,
        ),
        room(
            "attached_bathroom_1",
            RoomType.ATTACHED_BATHROOM,
            "Attached Bathroom",
            min_width=1.5,
            max_width=3.0,
            min_height=1.5,
            max_height=3.0,
            min_area=3.0,
            max_area=8.0,
        ),
    )

    relations = (
        RoomRelationSpec(
            source_room_id=RoomId("kitchen_1"),
            target_room_ids=(RoomId("dining_room_1"),),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.SOFT,
        ),
        RoomRelationSpec(
            source_room_id=RoomId("living_room_1"),
            target_room_ids=(RoomId("kitchen_1"), RoomId("veranda_1")),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.SOFT,
        ),
        RoomRelationSpec(
            source_room_id=RoomId("bedroom_1"),
            target_room_ids=(RoomId("attached_bathroom_1"),),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.SOFT,
        ),
        RoomRelationSpec(
            source_room_id=RoomId("hallway_1"),
            target_room_ids=(RoomId("bedroom_1"), RoomId("bedroom_2")),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.SOFT,
        ),
        RoomRelationSpec(
            source_room_id=RoomId("bathroom_1"),
            target_room_ids=(RoomId("hallway_1"), RoomId("living_room_1")),
            match_policy=MatchPolicy.OR,
            strength=ConstraintStrength.SOFT,
        ),
    )

    return FloorPlanGenerationSpec(
        floor=FloorSpec(width=20.0, height=16.0),
        rooms=rooms,
        room_relations=relations,
    )


def build_first_candidate() -> tuple[CandidatePoint, ...]:
    """A deliberately reasonable arrangement for an easy-to-read first trial."""
    positions = {
        "veranda_1": (10.0, 1.0),
        "garage_1": (2.0, 2.0),
        "living_room_1": (10.0, 4.0),
        "kitchen_1": (16.0, 7.0),
        "dining_room_1": (13.0, 7.0),
        "hallway_1": (10.0, 9.0),
        "bedroom_1": (5.0, 12.0),
        "bedroom_2": (10.0, 13.0),
        "bathroom_1": (15.0, 12.0),
        "attached_bathroom_1": (5.0, 14.0),
    }

    return tuple(
        CandidatePoint(RoomId(room_id), x, y) for room_id, (x, y) in positions.items()
    )


def build_random_candidate(
    specification: FloorPlanGenerationSpec,
    rng: random.Random,
) -> tuple[CandidatePoint, ...]:
    """Mock the search stage by sampling unique points from a simple grid."""
    x_count = int(specification.floor.width / GRID_RESOLUTION)
    y_count = int(specification.floor.height / GRID_RESOLUTION)

    grid_points = [
        (x * GRID_RESOLUTION, y * GRID_RESOLUTION)
        for x in range(x_count + 1)
        for y in range(y_count + 1)
    ]

    selected_positions = rng.sample(grid_points, k=len(specification.rooms))

    return tuple(
        CandidatePoint(room_spec.id, x, y)
        for room_spec, (x, y) in zip(
            specification.rooms,
            selected_positions,
            strict=True,
        )
    )


def print_trial(
    trial_number: int,
    candidate: tuple[CandidatePoint, ...],
    result: ScoringResult,
) -> None:
    print("\n" + "=" * 78)
    print(f"TRIAL {trial_number:02d}/{TRIAL_COUNT}")
    print("=" * 78)

    for point in candidate:
        print(f"{str(point.room_id):24} x={point.x:5.1f}  y={point.y:5.1f}")

    print("-" * 78)
    for evaluator in result.evaluator_results:
        raw_score = (
            "N/A" if evaluator.raw_score is None else f"{evaluator.raw_score:.2f}"
        )
        print(
            f"{str(evaluator.evaluator_key):26} "
            f"status={evaluator.status.value:12} "
            f"raw={raw_score:>7} "
            f"contribution={evaluator.contribution:6.2f}"
        )

    print("-" * 78)
    print(f"TOTAL SCORE: {result.total_score:.2f}")
    print(f"PASSED CRITICAL CHECKS: {result.passed_critical_checks}")

    if result.stop_reason:
        print(f"STOP REASON: {result.stop_reason}")


def main() -> None:
    specification = build_mock_specification()
    registry = create_default_registry()
    config = create_default_config()
    rng = random.Random(RANDOM_SEED)

    best_trial = 0
    best_candidate: tuple[CandidatePoint, ...] | None = None
    best_result: ScoringResult | None = None

    print("Candidate-scoring component run")
    print(f"Trials: {TRIAL_COUNT} | Seed: {RANDOM_SEED} | Grid: {GRID_RESOLUTION}")

    for trial_number in range(1, TRIAL_COUNT + 1):
        candidate = (
            build_first_candidate()
            if trial_number == 1
            else build_random_candidate(specification, rng)
        )

        result = evaluate_candidate(
            CandidateScoringInput(
                specification=specification,
                candidate=candidate,
            ),
            registry=registry,
            config=config,
        )

        print_trial(trial_number, candidate, result)

        if best_result is None or result.total_score > best_result.total_score:
            best_trial = trial_number
            best_candidate = candidate
            best_result = result

    assert best_candidate is not None
    assert best_result is not None

    print("\n" + "#" * 78)
    print(f"BEST TRIAL: {best_trial:02d} | SCORE: {best_result.total_score:.2f}")
    print("#" * 78)
    for point in best_candidate:
        print(f"{str(point.room_id):24} x={point.x:5.1f}  y={point.y:5.1f}")


if __name__ == "__main__":
    main()
