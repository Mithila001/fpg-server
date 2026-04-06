from ortools.sat.python import cp_model

from app.algorithms.fpg_opening.constraints.internal_doors_placement import (
    add_internal_doors_placement_constraint,
)
from app.algorithms.fpg_opening.utils.geometry import get_internal_door_candidates, normalize_rooms


def _solve_selected(candidates: list[dict]) -> tuple[list[int], int]:
    model = cp_model.CpModel()
    decisions = add_internal_doors_placement_constraint(model=model, candidates=candidates)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    selected_indices = [
        index
        for index, selected_var in enumerate(decisions["selected"])
        if solver.Value(selected_var) == 1
    ]
    return selected_indices, len(selected_indices)


def test_internal_door_candidate_requires_min_shared_overlap_of_10() -> None:
    rooms = normalize_rooms(
        [
            {"name": "bed_1", "type": "bedroom", "x": 0, "y": 0, "w": 10, "h": 20},
            {"name": "living_1", "type": "livingRoom", "x": 10, "y": 0, "w": 10, "h": 9},
        ]
    )

    candidates = get_internal_door_candidates(
        all_rooms=rooms,
        preferred_door_length=8.0,
    )

    assert candidates == []

    rooms_overlap_10 = normalize_rooms(
        [
            {"name": "bed_1", "type": "bedroom", "x": 0, "y": 0, "w": 10, "h": 20},
            {"name": "living_1", "type": "livingRoom", "x": 10, "y": 0, "w": 10, "h": 10},
        ]
    )

    candidates_overlap_10 = get_internal_door_candidates(
        all_rooms=rooms_overlap_10,
        preferred_door_length=8.0,
    )

    assert len(candidates_overlap_10) == 1


def test_internal_door_bedroom_attachedbathroom_is_eligible() -> None:
    candidates = [
        {
            "room_a_name": "bed_1",
            "room_a_type": "bedroom",
            "room_b_name": "abath_1",
            "room_b_type": "attachedbathroom",
            "side": "east",
            "x1": 10.0,
            "y1": 1.0,
            "x2": 10.0,
            "y2": 9.0,
        }
    ]

    selected_indices, selected_count = _solve_selected(candidates)

    assert selected_count == 1
    assert selected_indices == [0]


def test_internal_door_attachedbathroom_to_hallway_is_not_eligible() -> None:
    candidates = [
        {
            "room_a_name": "abath_1",
            "room_a_type": "attachedbathroom",
            "room_b_name": "hall_1",
            "room_b_type": "hallway",
            "side": "east",
            "x1": 10.0,
            "y1": 1.0,
            "x2": 10.0,
            "y2": 9.0,
        }
    ]

    selected_indices, selected_count = _solve_selected(candidates)

    assert selected_count == 0
    assert selected_indices == []


def test_internal_door_bedroom_prefers_hallway_over_livingroom_when_both_exist() -> None:
    candidates = [
        {
            "room_a_name": "bed_1",
            "room_a_type": "bedroom",
            "room_b_name": "living_1",
            "room_b_type": "livingRoom",
            "side": "east",
            "x1": 10.0,
            "y1": 1.0,
            "x2": 10.0,
            "y2": 9.0,
        },
        {
            "room_a_name": "bed_1",
            "room_a_type": "bedroom",
            "room_b_name": "hall_1",
            "room_b_type": "hallway",
            "side": "west",
            "x1": 0.0,
            "y1": 1.0,
            "x2": 0.0,
            "y2": 9.0,
        },
    ]

    selected_indices, selected_count = _solve_selected(candidates)

    assert selected_count == 1
    assert selected_indices == [1]


def test_internal_door_bedroom_allows_one_social_plus_one_attachedbathroom() -> None:
    candidates = [
        {
            "room_a_name": "bed_1",
            "room_a_type": "bedroom",
            "room_b_name": "living_1",
            "room_b_type": "livingRoom",
            "side": "east",
            "x1": 10.0,
            "y1": 1.0,
            "x2": 10.0,
            "y2": 9.0,
        },
        {
            "room_a_name": "bed_1",
            "room_a_type": "bedroom",
            "room_b_name": "hall_1",
            "room_b_type": "hallway",
            "side": "west",
            "x1": 0.0,
            "y1": 1.0,
            "x2": 0.0,
            "y2": 9.0,
        },
        {
            "room_a_name": "bed_1",
            "room_a_type": "bedroom",
            "room_b_name": "abath_1",
            "room_b_type": "attachedbathroom",
            "side": "north",
            "x1": 1.0,
            "y1": 10.0,
            "x2": 9.0,
            "y2": 10.0,
        },
    ]

    selected_indices, selected_count = _solve_selected(candidates)

    assert selected_count == 2
    assert 1 in selected_indices  # bedroom-hallway preferred over bedroom-livingroom
    assert 2 in selected_indices  # bedroom-attachedbathroom can coexist with one social door


def test_internal_door_kitchen_is_limited_to_one_internal_connection() -> None:
    candidates = [
        {
            "room_a_name": "kitchen_1",
            "room_a_type": "kitchen",
            "room_b_name": "living_1",
            "room_b_type": "livingRoom",
            "side": "east",
            "x1": 10.0,
            "y1": 1.0,
            "x2": 10.0,
            "y2": 9.0,
        },
        {
            "room_a_name": "kitchen_1",
            "room_a_type": "kitchen",
            "room_b_name": "hall_1",
            "room_b_type": "hallway",
            "side": "west",
            "x1": 0.0,
            "y1": 1.0,
            "x2": 0.0,
            "y2": 9.0,
        },
    ]

    selected_indices, selected_count = _solve_selected(candidates)

    assert selected_count == 1
    assert selected_indices in ([0], [1])
