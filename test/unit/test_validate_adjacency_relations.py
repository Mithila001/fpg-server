import pytest

from app.algorithms.fpg_rooms.fpg_score.score_critical.adjacency_relations import (
    validate_adjacency_relations,
)
from app.algorithms.fpg_rooms.types.room_relations_constraints import RoomRelationsConstraint


def make_room(name: str, type_: str, x: int, y: int, x_end: int, y_end: int) -> dict:
    return {
        "name": name,
        "type": type_,
        "x": x,
        "y": y,
        "x_end": x_end,
        "y_end": y_end,
    }


def test_validate_adjacency_relations_hard_and_requires_all_related_types():
    rooms = [
        make_room("bedroom1", "bedroom", 0, 0, 10, 10),
        make_room("livingRoom1", "livingRoom", 10, 0, 20, 10),
        make_room("hallway1", "hallway", 0, 10, 10, 20),
    ]
    relation_rule = RoomRelationsConstraint(
        room_type="bedroom",
        related_room=["livingRoom", "hallway"],
        constraint_level="hard_AND",
    )

    violations = validate_adjacency_relations(rooms, [relation_rule], min_overlap=1)

    assert violations == []


def test_validate_adjacency_relations_hard_or_allows_any_related_type():
    rooms = [
        make_room("bedroom1", "bedroom", 0, 0, 10, 10),
        make_room("livingRoom1", "livingRoom", 10, 0, 20, 10),
        make_room("hallway1", "hallway", 20, 20, 30, 30),
    ]
    relation_rule = RoomRelationsConstraint(
        room_type="bedroom",
        related_room=["livingRoom", "hallway"],
        constraint_level="hard_OR",
    )

    violations = validate_adjacency_relations(rooms, [relation_rule], min_overlap=1)

    assert violations == []


def test_validate_adjacency_relations_hard_or_reports_missing_any_relation():
    rooms = [
        make_room("bedroom1", "bedroom", 0, 0, 10, 10),
        make_room("livingRoom1", "livingRoom", 20, 20, 30, 30),
        make_room("hallway1", "hallway", 40, 40, 50, 50),
    ]
    relation_rule = {
        "room_type": "bedroom",
        "related_room": ["livingRoom", "hallway"],
        "constraint_level": "hard_OR",
    }

    violations = validate_adjacency_relations(rooms, [relation_rule], min_overlap=1)

    assert violations == [
        "Adjacency rule unsatisfied for 'bedroom1' (bedroom): must touch at least one room of type 'livingRoom' or 'hallway'"
    ]


def test_validate_adjacency_relations_rejects_unrecognized_constraint_level():
    rooms = [
        make_room("bedroom1", "bedroom", 0, 0, 10, 10),
        make_room("livingRoom1", "livingRoom", 10, 0, 20, 10),
    ]
    relation_rule = {
        "room_type": "bedroom",
        "related_room": ["livingRoom"],
        "constraint_level": "soft",
    }

    with pytest.raises(ValueError, match="Unknown constraint_level"):
        validate_adjacency_relations(rooms, [relation_rule], min_overlap=1)
