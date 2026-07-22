"""Run the real Candidate Search feature with realistic mock data.

The execution flow is:

    mock floor-plan specification
        -> search_candidates()
        -> Optuna trial generation
        -> candidate scoring evaluator
        -> visualization API
        -> PNG saved for every trial

Run from the repository root:

    python test/algorithms/candidate_search/run_candidate_search.py
"""

from __future__ import annotations

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    ScoringResult,
    create_default_config,
    create_default_registry,
    evaluate_candidate,
)
from app.algorithms.candidate_search import (
    CandidatePoint,
    CandidateSearchInput,
    CandidateSearchSettings,
    CandidateSearchTarget,
    search_candidates,
)
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
    min_length: float,
    max_length: float,
    min_area: float,
    max_area: float,
) -> RoomSpec:
    """Create one room specification."""

    return RoomSpec(
        id=RoomId(room_id),
        room_type=room_type,
        name=name,
        size=RoomSizeSpec(
            min_width=min_width,
            max_width=max_width,
            min_length=min_length,
            max_length=max_length,
            min_area=min_area,
            max_area=max_area,
        ),
    )


def build_mock_specification() -> FloorPlanGenerationSpec:
    """Create a realistic small residential floor-plan specification."""

    rooms = (
        room(
            "veranda_1",
            RoomType.VERANDA,
            "Veranda",
            min_width=3.0,
            max_width=8.0,
            min_length=2.0,
            max_length=4.0,
            min_area=6.0,
            max_area=24.0,
        ),
        room(
            "garage_1",
            RoomType.GARAGE,
            "Garage",
            min_width=3.0,
            max_width=6.0,
            min_length=5.0,
            max_length=8.0,
            min_area=15.0,
            max_area=40.0,
        ),
        room(
            "living_room_1",
            RoomType.LIVING_ROOM,
            "Living Room",
            min_width=4.0,
            max_width=8.0,
            min_length=4.0,
            max_length=7.0,
            min_area=20.0,
            max_area=42.0,
        ),
        room(
            "kitchen_1",
            RoomType.KITCHEN,
            "Kitchen",
            min_width=3.0,
            max_width=5.0,
            min_length=3.0,
            max_length=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "dining_room_1",
            RoomType.DINING_ROOM,
            "Dining Room",
            min_width=3.0,
            max_width=5.0,
            min_length=3.0,
            max_length=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "hallway_1",
            RoomType.HALLWAY,
            "Hallway",
            min_width=1.0,
            max_width=2.5,
            min_length=4.0,
            max_length=12.0,
            min_area=5.0,
            max_area=20.0,
        ),
        room(
            "bedroom_1",
            RoomType.BEDROOM,
            "Bedroom 1",
            min_width=3.0,
            max_width=5.0,
            min_length=3.0,
            max_length=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "bedroom_2",
            RoomType.BEDROOM,
            "Bedroom 2",
            min_width=3.0,
            max_width=5.0,
            min_length=3.0,
            max_length=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "bathroom_1",
            RoomType.BATHROOM,
            "Bathroom",
            min_width=2.0,
            max_width=4.0,
            min_length=2.0,
            max_length=4.0,
            min_area=4.0,
            max_area=12.0,
        ),
        room(
            "attached_bathroom_1",
            RoomType.ATTACHED_BATHROOM,
            "Attached Bathroom",
            min_width=1.5,
            max_width=3.0,
            min_length=1.5,
            max_length=3.0,
            min_area=3.0,
            max_area=8.0,
        ),
    )

    room_relations = (
        RoomRelationSpec(
            source_room_id=RoomId("kitchen_1"),
            target_room_ids=(RoomId("dining_room_1"),),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.SOFT,
        ),
        RoomRelationSpec(
            source_room_id=RoomId("living_room_1"),
            target_room_ids=(
                RoomId("kitchen_1"),
                RoomId("veranda_1"),
            ),
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
            target_room_ids=(
                RoomId("bedroom_1"),
                RoomId("bedroom_2"),
            ),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.SOFT,
        ),
        RoomRelationSpec(
            source_room_id=RoomId("bathroom_1"),
            target_room_ids=(
                RoomId("hallway_1"),
                RoomId("living_room_1"),
            ),
            match_policy=MatchPolicy.OR,
            strength=ConstraintStrength.SOFT,
        ),
    )

    return FloorPlanGenerationSpec(
        floor=FloorSpec(
            width=20.0,
            length=16.0,
        ),
        rooms=rooms,
        room_relations=room_relations,
    )


def print_trial(
    trial_number: int,
    points: tuple[CandidatePoint, ...],
    scoring_result: ScoringResult,
) -> None:
    """Print the candidate coordinates and scoring result for one trial."""

    print("\n" + "=" * 78)
    print(f"TRIAL {trial_number:02d}/{TRIAL_COUNT}")
    print("=" * 78)

    for point in points:
        print(f"{str(point.room_id):24} x={point.x:5.1f}  y={point.y:5.1f}")

    print("-" * 78)

    for evaluator_result in scoring_result.evaluator_results:
        raw_score = (
            "N/A"
            if evaluator_result.raw_score is None
            else f"{evaluator_result.raw_score:.2f}"
        )

        print(
            f"{str(evaluator_result.evaluator_key):26} "
            f"status={evaluator_result.status.value:12} "
            f"raw={raw_score:>7} "
            f"contribution={evaluator_result.contribution:6.2f}"
        )

    print("-" * 78)
    print(f"TOTAL SCORE: {scoring_result.total_score:.2f}")
    print(f"PASSED CRITICAL CHECKS: {scoring_result.passed_critical_checks}")

    if scoring_result.stop_reason:
        print(f"STOP REASON: {scoring_result.stop_reason}")


def print_final_result(
    points: tuple[CandidatePoint, ...],
    *,
    score: float,
    completed_trials: int,
) -> None:
    """Print the best Candidate Search result."""

    print("\n" + "#" * 78)
    print("CANDIDATE SEARCH COMPLETED")
    print("#" * 78)

    print(f"Completed trials: {completed_trials}")
    print(f"Best score: {score:.2f}")

    print("\nBest candidate points:")

    for point in points:
        print(f"{str(point.room_id):24} x={point.x:5.1f}  y={point.y:5.1f}")


def main() -> None:
    specification = build_mock_specification()

    scoring_registry = create_default_registry()
    scoring_config = create_default_config()

    completed_evaluations = 0

    def score_candidate(
        points: tuple[CandidatePoint, ...],
    ) -> float:
        """Candidate Search callback used to evaluate one Optuna trial."""

        nonlocal completed_evaluations

        scoring_result = evaluate_candidate(
            CandidateScoringInput(
                specification=specification,
                candidate=points,
            ),
            registry=scoring_registry,
            config=scoring_config,
        )

        completed_evaluations += 1

        print_trial(
            completed_evaluations,
            points,
            scoring_result,
        )

        return scoring_result.total_score

    search_input = CandidateSearchInput(
        targets=tuple(
            CandidateSearchTarget(room_spec.id) for room_spec in specification.rooms
        ),
        settings=CandidateSearchSettings(
            min_x=0.0,
            max_x=specification.floor.width,
            min_y=0.0,
            max_y=specification.floor.length,
            grid_resolution=GRID_RESOLUTION,
            trial_count=TRIAL_COUNT,
            random_seed=RANDOM_SEED,
        ),
        evaluator=score_candidate,
    )

    print("Candidate Search realistic component run")
    print(f"Rooms: {len(specification.rooms)}")
    print(f"Trials: {TRIAL_COUNT}")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Grid resolution: {GRID_RESOLUTION}")
    print(
        "Search bounds: "
        f"(0.0, 0.0) -> "
        f"({specification.floor.width}, "
        f"{specification.floor.length})"
    )

    result = search_candidates(search_input)

    print_final_result(
        result.points,
        score=result.score,
        completed_trials=result.completed_trials,
    )


if __name__ == "__main__":
    main()
