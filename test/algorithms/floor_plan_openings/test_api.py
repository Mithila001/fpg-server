from __future__ import annotations

import copy
from dataclasses import replace

from app.algorithms.floor_plan_openings import (
    DEFAULT_OPENING_PROFILE,
    OpeningGenerationRequest,
    OpeningGenerationStatus,
    generate_openings,
)
from app.algorithms.types_new import (
    FloorPlan,
    FloorPlanOpening,
    OpeningId,
    OpeningPurpose,
    OpeningType,
    Point,
    RoomId,
    RoomType,
)

from .conftest import rectangle, room, two_room_plan


def test_default_api_generates_combined_openings_without_mutating_input() -> None:
    plan = two_room_plan()
    snapshot = copy.deepcopy(plan)
    result = generate_openings(OpeningGenerationRequest(plan))

    assert result.status is OpeningGenerationStatus.OPTIMAL
    assert result.solved
    assert result.floor_plan is not None
    assert result.floor_plan is not plan
    assert result.floor_plan.rooms is not plan.rooms
    assert plan == snapshot
    purposes = [opening.purpose for opening in result.floor_plan.openings]
    assert purposes.count(OpeningPurpose.MAIN_ENTRANCE) == 1
    assert purposes.count(OpeningPurpose.SECONDARY_ENTRANCE) == 1
    assert purposes.count(OpeningPurpose.ROOM_CONNECTION) == 1
    assert purposes.count(OpeningPurpose.DAYLIGHT) == 2


def test_repeated_runs_have_identical_openings_and_ids() -> None:
    plan = two_room_plan()
    first = generate_openings(OpeningGenerationRequest(plan))
    second = generate_openings(OpeningGenerationRequest(plan))
    assert first.floor_plan is not None and second.floor_plan is not None
    assert first.floor_plan.openings == second.floor_plan.openings


def test_veranda_connection_is_the_only_main_entrance() -> None:
    plan = FloorPlan(
        rectangle(0, 0, 20, 20),
        [
            room("veranda", RoomType.VERANDA, rectangle(0, 0, 20, 5)),
            room("living", RoomType.LIVING_ROOM, rectangle(0, 5, 20, 20)),
        ],
    )
    result = generate_openings(OpeningGenerationRequest(plan))
    assert result.floor_plan is not None
    entrances = [
        opening
        for opening in result.floor_plan.openings
        if opening.purpose is OpeningPurpose.MAIN_ENTRANCE
    ]
    assert len(entrances) == 1
    assert set(entrances[0].connected_room_ids) == {
        RoomId("living"),
        RoomId("veranda"),
    }


def test_attached_bedroom_receives_bathroom_and_social_doors() -> None:
    plan = FloorPlan(
        rectangle(0, 0, 30, 20),
        [
            room("bed", RoomType.BEDROOM, rectangle(0, 0, 10, 10)),
            room("bath", RoomType.ATTACHED_BATHROOM, rectangle(0, 10, 10, 20)),
            room("hall", RoomType.HALLWAY, rectangle(10, 0, 20, 20)),
            room("living", RoomType.LIVING_ROOM, rectangle(20, 0, 30, 20)),
        ],
    )
    result = generate_openings(OpeningGenerationRequest(plan))
    assert result.floor_plan is not None
    bedroom_doors = [
        opening
        for opening in result.floor_plan.openings
        if opening.opening_type is OpeningType.DOOR
        and RoomId("bed") in opening.connected_room_ids
    ]
    assert len(bedroom_doors) == 2
    assert any(RoomId("bath") in opening.connected_room_ids for opening in bedroom_doors)
    assert any(RoomId("hall") in opening.connected_room_ids for opening in bedroom_doors)


def test_missing_optional_window_is_reported() -> None:
    plan = FloorPlan(
        rectangle(0, 0, 6, 6),
        [room("living", RoomType.LIVING_ROOM, rectangle(0, 0, 6, 6))],
    )
    result = generate_openings(OpeningGenerationRequest(plan))
    assert result.solved
    assert any(
        issue.code == "no_candidate" and issue.demand_id == "window:living"
        for issue in result.diagnostics.issues
    )
    assert any(
        issue.code == "undersized_exterior_door"
        for issue in result.diagnostics.issues
    )


def test_existing_openings_produce_structured_invalid_input() -> None:
    plan = two_room_plan()
    plan.openings.append(
        FloorPlanOpening(
            OpeningId("existing"),
            OpeningType.DOOR,
            OpeningPurpose.MAIN_ENTRANCE,
            Point(0, 1),
            Point(0, 9),
            (RoomId("living"),),
        )
    )
    result = generate_openings(OpeningGenerationRequest(plan))
    assert result.status is OpeningGenerationStatus.INVALID_INPUT
    assert result.floor_plan is None
    assert result.diagnostics.issues[0].code == "invalid_input"


def test_window_and_door_on_same_wall_observe_clearance() -> None:
    plan = FloorPlan(
        rectangle(0, 0, 30, 10),
        [room("living", RoomType.LIVING_ROOM, rectangle(0, 0, 30, 10))],
    )
    policy = replace(
        DEFAULT_OPENING_PROFILE.policy,
        window_side_priority=("south", "north", "east", "west"),
    )
    profile = replace(DEFAULT_OPENING_PROFILE, policy=policy)
    result = generate_openings(OpeningGenerationRequest(plan, profile))
    assert result.floor_plan is not None
    south = [
        opening
        for opening in result.floor_plan.openings
        if opening.start.y == opening.end.y == 0
    ]
    assert len(south) == 2
    intervals = sorted((opening.start.x, opening.end.x) for opening in south)
    assert intervals[1][0] - intervals[0][1] >= 5
