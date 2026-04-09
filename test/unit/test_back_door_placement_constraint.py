from ortools.sat.python import cp_model

from app.algorithms.fpg_opening.constraints.back_door_placement import (
    add_back_door_placement_constraint,
    build_back_door_candidates,
)
from app.algorithms.fpg_opening.utils.geometry import normalize_rooms


def _solve_selected_index(candidates: list[dict]) -> int:
    model = cp_model.CpModel()
    decision_vars = add_back_door_placement_constraint(model=model, candidates=candidates)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    selected_indices = [
        index
        for index, selected_var in enumerate(decision_vars["selected"])
        if solver.Value(selected_var) == 1
    ]
    assert len(selected_indices) == 1
    return selected_indices[0]


def test_back_door_no_kitchen_or_hallway_returns_no_candidates() -> None:
    rooms = normalize_rooms(
        [
            {"name": "living_1", "type": "livingRoom", "x": 0, "y": 0, "w": 20, "h": 20},
            {"name": "bed_1", "type": "bedroom", "x": 25, "y": 0, "w": 20, "h": 20},
        ]
    )

    candidates = build_back_door_candidates(
        all_rooms=rooms,
        preferred_door_length=8.0,
    )

    assert candidates == []


def test_back_door_selects_furthest_back_horizontal_and_prefers_kitchen_on_tie() -> None:
    rooms = normalize_rooms(
        [
            {"name": "hallway_back", "type": "hallway", "x": 0, "y": 20, "w": 20, "h": 20},
            {"name": "kitchen_back", "type": "kitchen", "x": 30, "y": 20, "w": 20, "h": 20},
            {"name": "kitchen_front", "type": "kitchen", "x": 60, "y": 10, "w": 20, "h": 20},
        ]
    )

    candidates = build_back_door_candidates(
        all_rooms=rooms,
        preferred_door_length=8.0,
    )

    assert candidates
    assert all(candidate["side"] == "north" for candidate in candidates)
    selected_index = _solve_selected_index(candidates)
    selected = candidates[selected_index]

    assert selected["room_name"] == "kitchen_back"
    assert selected["side"] == "north"
    assert selected["y1"] == selected["y2"]


def test_back_door_falls_back_to_outermost_vertical_when_no_horizontal_outer_wall() -> None:
    rooms = normalize_rooms(
        [
            {"name": "kitchen_1", "type": "kitchen", "x": 10, "y": 10, "w": 20, "h": 20},
            {"name": "blocker_1", "type": "bedroom", "x": 10, "y": 30, "w": 20, "h": 10},
            {"name": "hallway_1", "type": "hallway", "x": 50, "y": 12, "w": 20, "h": 20},
            {"name": "blocker_2", "type": "livingRoom", "x": 50, "y": 32, "w": 20, "h": 8},
        ]
    )

    candidates = build_back_door_candidates(
        all_rooms=rooms,
        preferred_door_length=8.0,
    )

    assert candidates
    assert all(candidate["side"] in {"west", "east"} for candidate in candidates)

    selected_index = _solve_selected_index(candidates)
    selected = candidates[selected_index]
    assert selected["side"] in {"west", "east"}
    assert selected["x1"] == selected["x2"]