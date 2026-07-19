from __future__ import annotations

import pytest

from app.algorithms.floor_plan_scoring import ScoringInputError, score_floor_plan
from app.algorithms.types_new import (
    ConstraintStrength,
    FloorPlan,
    FloorPlanGenerationSpec,
    FloorPlanRoom,
    FloorSpec,
    MatchPolicy,
    Point,
    Polygon,
    RoomId,
    RoomRelationSpec,
    RoomSizeSpec,
    RoomSpec,
    RoomType,
)


SIZE = RoomSizeSpec(2, 10, 2, 10, 4, 100)


def _polygon(x1, y1, x2, y2):
    return Polygon((Point(x1, y1), Point(x2, y1), Point(x2, y2), Point(x1, y2)))


def _spec(*rooms, relations=()):
    return FloorPlanGenerationSpec(FloorSpec(20, 10), tuple(rooms), tuple(relations))


def _room(room_id, room_type, boundary):
    return FloorPlanRoom(RoomId(room_id), room_type, room_id, boundary)


def test_scoring_accepts_merged_room_identity_redirect():
    specification = _spec(
        RoomSpec(RoomId("hallway_1"), RoomType.HALLWAY, "Hallway 1", SIZE),
        RoomSpec(RoomId("hallway_2"), RoomType.HALLWAY, "Hallway 2", SIZE),
    )
    plan = FloorPlan(
        _polygon(0, 0, 20, 10),
        [_room("hallway_1", RoomType.HALLWAY, _polygon(0, 0, 20, 10))],
        identity_redirects={RoomId("hallway_2"): RoomId("hallway_1")},
    )

    result = score_floor_plan(plan, specification)

    assert result.total_score >= 0


def test_redirected_relation_uses_surviving_room_geometry():
    relation = RoomRelationSpec(
        RoomId("hallway_2"),
        (RoomId("bedroom_1"),),
        MatchPolicy.AND,
        ConstraintStrength.HARD,
    )
    specification = _spec(
        RoomSpec(RoomId("hallway_1"), RoomType.HALLWAY, "Hallway 1", SIZE),
        RoomSpec(RoomId("hallway_2"), RoomType.HALLWAY, "Hallway 2", SIZE),
        RoomSpec(RoomId("bedroom_1"), RoomType.BEDROOM, "Bedroom", SIZE),
        relations=(relation,),
    )
    plan = FloorPlan(
        _polygon(0, 0, 20, 10),
        [
            _room("hallway_1", RoomType.HALLWAY, _polygon(0, 0, 10, 10)),
            _room("bedroom_1", RoomType.BEDROOM, _polygon(10, 0, 20, 10)),
        ],
        identity_redirects={RoomId("hallway_2"): RoomId("hallway_1")},
    )

    result = score_floor_plan(plan, specification)

    required_adjacency = next(
        item
        for item in result.evaluator_results
        if str(item.evaluator_key) == "required_adjacency"
    )
    assert required_adjacency.passed_threshold is True


@pytest.mark.parametrize(
    "redirects, expected_message",
    [
        (
            {RoomId("hallway_2"): RoomId("hallway_2")},
            "cycle",
        ),
        (
            {RoomId("hallway_2"): RoomId("hallway_3")},
            "surviving room",
        ),
    ],
)
def test_scoring_rejects_invalid_redirects(redirects, expected_message):
    specification = _spec(
        RoomSpec(RoomId("hallway_1"), RoomType.HALLWAY, "Hallway 1", SIZE),
        RoomSpec(RoomId("hallway_2"), RoomType.HALLWAY, "Hallway 2", SIZE),
        RoomSpec(RoomId("hallway_3"), RoomType.HALLWAY, "Hallway 3", SIZE),
    )
    plan = FloorPlan(
        _polygon(0, 0, 20, 10),
        [_room("hallway_1", RoomType.HALLWAY, _polygon(0, 0, 20, 10))],
        identity_redirects=redirects,
    )

    with pytest.raises(ScoringInputError, match=expected_message):
        score_floor_plan(plan, specification)
