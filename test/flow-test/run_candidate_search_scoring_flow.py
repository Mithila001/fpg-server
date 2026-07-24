"""Run Candidate Search and Candidate Scoring together in a mock environment.

This is an isolated flow test. It intentionally does not import anything from
``test/algorithms``; only the public application APIs are used.

Flow:

    mock FloorPlanGenerationSpec
        -> search_candidates()
        -> scoring callback for every Optuna trial
        -> evaluate_candidate()
        -> best scored candidate
        -> integration assertions

Run from the repository root:

    python -m test.flow-test.run_candidate_search_scoring_flow
"""

from __future__ import annotations

from math import isclose

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
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
SCORE_TOLERANCE = 1e-9


def room(
    room_id: str,
    room_type: RoomType,
    name: str,
    *,
    min_width: float,
    max_width: float,
    min_area: float,
    max_area: float,
) -> RoomSpec:
    """Build one room specification for the mock flow."""

    return RoomSpec(
        id=RoomId(room_id),
        room_type=room_type,
        name=name,
        size=RoomSizeSpec(
            min_width=min_width,
            max_width=max_width,
            min_area=min_area,
            max_area=max_area,
        ),
    )


def build_mock_specification() -> FloorPlanGenerationSpec:
    """Build a realistic small single-story residential specification."""

    rooms = (
        room(
            "veranda_1",
            RoomType.VERANDA,
            "Veranda",
            min_width=3.0,
            max_width=8.0,
            min_area=6.0,
            max_area=24.0,
        ),
        room(
            "garage_1",
            RoomType.GARAGE,
            "Garage",
            min_width=3.0,
            max_width=6.0,
            min_area=15.0,
            max_area=40.0,
        ),
        room(
            "living_room_1",
            RoomType.LIVING_ROOM,
            "Living Room",
            min_width=4.0,
            max_width=8.0,
            min_area=20.0,
            max_area=42.0,
        ),
        room(
            "kitchen_1",
            RoomType.KITCHEN,
            "Kitchen",
            min_width=3.0,
            max_width=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "dining_room_1",
            RoomType.DINING_ROOM,
            "Dining Room",
            min_width=3.0,
            max_width=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "hallway_1",
            RoomType.HALLWAY,
            "Hallway",
            min_width=1.0,
            max_width=2.5,
            min_area=5.0,
            max_area=20.0,
        ),
        room(
            "bedroom_1",
            RoomType.BEDROOM,
            "Bedroom 1",
            min_width=3.0,
            max_width=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "bedroom_2",
            RoomType.BEDROOM,
            "Bedroom 2",
            min_width=3.0,
            max_width=5.0,
            min_area=9.0,
            max_area=20.0,
        ),
        room(
            "bathroom_1",
            RoomType.BATHROOM,
            "Bathroom",
            min_width=2.0,
            max_width=4.0,
            min_area=4.0,
            max_area=12.0,
        ),
        room(
            "attached_bathroom_1",
            RoomType.ATTACHED_BATHROOM,
            "Attached Bathroom",
            min_width=1.5,
            max_width=3.0,
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
        floor=FloorSpec(width=20.0, length=16.0),
        rooms=rooms,
        room_relations=room_relations,
    )


def assert_point_is_on_grid(
    value: float,
    *,
    minimum: float,
    resolution: float,
) -> None:
    """Assert that a sampled coordinate follows the configured search grid."""

    grid_position = (value - minimum) / resolution
    assert isclose(
        grid_position,
        round(grid_position),
        abs_tol=SCORE_TOLERANCE,
    ), f"Coordinate {value} is not aligned to grid resolution {resolution}."


def validate_flow_result(
    *,
    specification: FloorPlanGenerationSpec,
    result_points: tuple[CandidatePoint, ...],
    result_score: float,
    completed_trials: int,
    callback_count: int,
    rescored_best: float,
) -> None:
    """Validate the main Candidate Search -> Candidate Scoring integration."""

    expected_room_ids = {room_spec.id for room_spec in specification.rooms}
    returned_room_ids = {point.room_id for point in result_points}

    assert callback_count == TRIAL_COUNT, (
        f"Scoring callback ran {callback_count} times; expected {TRIAL_COUNT}."
    )
    assert completed_trials == TRIAL_COUNT, (
        f"Search completed {completed_trials} trials; expected {TRIAL_COUNT}."
    )
    assert len(result_points) == len(specification.rooms), (
        "Best candidate does not contain exactly one point per room."
    )
    assert returned_room_ids == expected_room_ids, (
        "Best candidate room IDs do not match the mock specification."
    )
    assert isclose(result_score, rescored_best, abs_tol=SCORE_TOLERANCE), (
        "Search result score differs from independently rescoring its points: "
        f"search={result_score}, rescored={rescored_best}."
    )

    for point in result_points:
        assert 0.0 <= point.x <= specification.floor.width
        assert 0.0 <= point.y <= specification.floor.length
        assert_point_is_on_grid(
            point.x,
            minimum=0.0,
            resolution=GRID_RESOLUTION,
        )
        assert_point_is_on_grid(
            point.y,
            minimum=0.0,
            resolution=GRID_RESOLUTION,
        )


def main() -> None:
    specification = build_mock_specification()
    scoring_registry = create_default_registry()
    scoring_config = create_default_config()

    callback_count = 0
    trial_scores: list[float] = []

    def score_candidate(points: tuple[CandidatePoint, ...]) -> float:
        """Evaluate one Candidate Search trial through Candidate Scoring."""

        nonlocal callback_count

        scoring_result = evaluate_candidate(
            CandidateScoringInput(
                specification=specification,
                candidate=points,
            ),
            registry=scoring_registry,
            config=scoring_config,
        )

        callback_count += 1
        trial_scores.append(scoring_result.total_score)

        print(
            f"Trial {callback_count:02d}/{TRIAL_COUNT}: "
            f"score={scoring_result.total_score:.2f} "
            f"critical_checks={scoring_result.passed_critical_checks}"
        )

        return scoring_result.total_score

    search_result = search_candidates(
        CandidateSearchInput(
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
    )

    rescored_best = evaluate_candidate(
        CandidateScoringInput(
            specification=specification,
            candidate=search_result.points,
        ),
        registry=scoring_registry,
        config=scoring_config,
    )

    validate_flow_result(
        specification=specification,
        result_points=search_result.points,
        result_score=search_result.score,
        completed_trials=search_result.completed_trials,
        callback_count=callback_count,
        rescored_best=rescored_best.total_score,
    )

    print("\nCandidate Search + Candidate Scoring flow passed")
    print(f"Completed trials: {search_result.completed_trials}")
    print(f"Best score: {search_result.score:.2f}")
    print(f"Observed score range: {min(trial_scores):.2f} -> {max(trial_scores):.2f}")
    print("Best candidate points:")

    for candidate_point in search_result.points:
        print(
            f"  {str(candidate_point.room_id):24} "
            f"x={candidate_point.x:5.1f} y={candidate_point.y:5.1f}"
        )


if __name__ == "__main__":
    main()
