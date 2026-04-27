from __future__ import annotations

from app.algorithms.fpg_rooms.fpg_optuna.runner import (
    _apply_side_lock_to_x_bounds,
    _opposite_side,
    _resolve_room_side_lock,
)


def test_opposite_side() -> None:
    assert _opposite_side("left") == "right"
    assert _opposite_side("right") == "left"


def test_room_side_lock_resolution_private_and_public() -> None:
    private_side = "left"
    public_side = "right"

    assert (
        _resolve_room_side_lock("bedroom", private_side=private_side, public_side=public_side)
        == "left"
    )
    assert (
        _resolve_room_side_lock("kitchen", private_side=private_side, public_side=public_side)
        == "right"
    )
    assert (
        _resolve_room_side_lock("garage", private_side=private_side, public_side=public_side)
        == "right"
    )
    assert (
        _resolve_room_side_lock("hallway", private_side=private_side, public_side=public_side)
        is None
    )


def test_apply_side_lock_to_x_bounds_left_right_and_none() -> None:
    min_x = 10.0
    max_x = 110.0

    left_min, left_max = _apply_side_lock_to_x_bounds(min_x=min_x, max_x=max_x, side="left")
    right_min, right_max = _apply_side_lock_to_x_bounds(
        min_x=min_x, max_x=max_x, side="right"
    )
    free_min, free_max = _apply_side_lock_to_x_bounds(min_x=min_x, max_x=max_x, side=None)

    assert left_min == 10.0
    assert left_max == 60.0

    assert right_min == 60.0
    assert right_max == 110.0

    assert free_min == min_x
    assert free_max == max_x
