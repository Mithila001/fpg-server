"""Run the real Candidate Scoring feature with five hardcoded candidates.

The execution flow mirrors the generation pipeline's Candidate Search callback:

    mock floor-plan specification
        -> CandidateScoringInput
        -> evaluate_candidate()
        -> total score printed for each candidate

Run from the repository root:

    python test/algorithms/candidate_scoring/run_candidate_scoring.py
"""

from __future__ import annotations

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
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
    """Create one room specification."""

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
    """Create the same realistic mock specification used by Candidate Search."""

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
        floor=FloorSpec(width=20.0, height=16.0),
        rooms=rooms,
        room_relations=room_relations,
    )


def point(room_id: str, x: float, y: float) -> CandidatePoint:
    """Create one hardcoded Candidate Search point."""

    return CandidatePoint(
        room_id=RoomId(room_id),
        x=x,
        y=y,
    )


def build_hardcoded_candidates() -> tuple[
    tuple[str, tuple[CandidatePoint, ...]],
    ...,
]:
    """Create five complete candidate inputs with intentionally varied layouts."""

    return (
        (
            "balanced_layout",
            (
                point("veranda_1", 10.0, 1.0),
                point("garage_1", 3.0, 3.0),
                point("living_room_1", 10.0, 5.0),
                point("kitchen_1", 14.0, 7.0),
                point("dining_room_1", 11.0, 7.0),
                point("hallway_1", 10.0, 10.0),
                point("bedroom_1", 6.0, 12.0),
                point("bedroom_2", 14.0, 12.0),
                point("bathroom_1", 11.0, 12.0),
                point("attached_bathroom_1", 5.0, 13.0),
            ),
        ),
        (
            "alternate_balanced_layout",
            (
                point("veranda_1", 8.0, 1.0),
                point("garage_1", 17.0, 3.0),
                point("living_room_1", 9.0, 5.0),
                point("kitchen_1", 5.0, 7.0),
                point("dining_room_1", 8.0, 7.0),
                point("hallway_1", 10.0, 10.0),
                point("bedroom_1", 6.0, 13.0),
                point("bedroom_2", 14.0, 13.0),
                point("bathroom_1", 11.0, 12.0),
                point("attached_bathroom_1", 5.0, 14.0),
            ),
        ),
        (
            "center_clustered_layout",
            (
                point("veranda_1", 8.0, 7.0),
                point("garage_1", 9.0, 7.0),
                point("living_room_1", 10.0, 7.0),
                point("kitchen_1", 11.0, 7.0),
                point("dining_room_1", 12.0, 7.0),
                point("hallway_1", 8.0, 9.0),
                point("bedroom_1", 9.0, 9.0),
                point("bedroom_2", 10.0, 9.0),
                point("bathroom_1", 11.0, 9.0),
                point("attached_bathroom_1", 12.0, 9.0),
            ),
        ),
        (
            "edge_heavy_layout",
            (
                point("veranda_1", 1.0, 1.0),
                point("garage_1", 19.0, 1.0),
                point("living_room_1", 1.0, 8.0),
                point("kitchen_1", 19.0, 8.0),
                point("dining_room_1", 1.0, 15.0),
                point("hallway_1", 10.0, 1.0),
                point("bedroom_1", 19.0, 15.0),
                point("bedroom_2", 10.0, 15.0),
                point("bathroom_1", 1.0, 12.0),
                point("attached_bathroom_1", 19.0, 12.0),
            ),
        ),
        (
            "poor_relationship_layout",
            (
                point("veranda_1", 18.0, 15.0),
                point("garage_1", 2.0, 14.0),
                point("living_room_1", 2.0, 2.0),
                point("kitchen_1", 18.0, 2.0),
                point("dining_room_1", 2.0, 8.0),
                point("hallway_1", 18.0, 8.0),
                point("bedroom_1", 3.0, 13.0),
                point("bedroom_2", 16.0, 13.0),
                point("bathroom_1", 3.0, 4.0),
                point("attached_bathroom_1", 17.0, 4.0),
            ),
        ),
    )


def main() -> None:
    specification = build_mock_specification()
    scoring_registry = create_default_registry()
    scoring_config = create_default_config()
    candidates = build_hardcoded_candidates()

    print("Candidate Scoring mock environment run")
    print(f"Rooms: {len(specification.rooms)}")
    print(f"Hardcoded candidates: {len(candidates)}")

    for index, (candidate_name, candidate_points) in enumerate(candidates, start=1):
        result = evaluate_candidate(
            CandidateScoringInput(
                specification=specification,
                candidate=candidate_points,
            ),
            registry=scoring_registry,
            config=scoring_config,
        )

        print(f"Candidate {index}: {candidate_name:<28} score={result.total_score:.2f}")


if __name__ == "__main__":
    main()
