from typing import List

from app.core.fpg_rooms.config_fpg import MAX_ASPECT_RATIO_HEIGHT, MAX_ASPECT_RATIO_WIDTH

from ...solver_models.room import Room


def add_basic_constraints(model, rooms: List[Room]) -> None:
    """Add no-overlap and aspect-ratio constraints to all rooms."""
    h_ratio = int(MAX_ASPECT_RATIO_HEIGHT)
    w_ratio = int(MAX_ASPECT_RATIO_WIDTH)

    x_intervals = [r.x_interval for r in rooms]
    y_intervals = [r.y_interval for r in rooms]
    model.AddNoOverlap2D(x_intervals, y_intervals)

    for room in rooms:
        model.Add(room.x + room.w == room.x_end)  # type: ignore
        model.Add(room.y + room.h == room.y_end)  # type: ignore

        if room.type == "hallway":
            continue

        model.Add(room.w * h_ratio <= room.h * w_ratio)  # type: ignore
        model.Add(room.h * h_ratio <= room.w * w_ratio)  # type: ignore
