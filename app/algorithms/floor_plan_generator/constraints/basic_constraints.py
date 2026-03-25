from typing import List
from ..solver_models.room import Room
from app.core.config_fpg import MAX_ASPECT_RATIO_HEIGHT, MAX_ASPECT_RATIO_WIDTH


def add_basic_constraints(model, rooms: List[Room]):
    """
    Adds no-overlap and aspect-ratio constraints to all rooms.

    Args:
        model: CpModel instance
        rooms: List of Room objects
    """
    h_ratio = int(MAX_ASPECT_RATIO_HEIGHT)
    w_ratio = int(MAX_ASPECT_RATIO_WIDTH)

    x_intervals = [r.x_interval for r in rooms]
    y_intervals = [r.y_interval for r in rooms]
    model.AddNoOverlap2D(x_intervals, y_intervals)

    for r in rooms:
        model.Add(r.x + r.w == r.x_end)  # type: ignore
        model.Add(r.y + r.h == r.y_end)  # type: ignore

        # Hallways use fixed-width / scalable-length — skip the global
        # aspect-ratio cap so they can be as elongated as needed.
        if r.type == "hallway":
            continue

        model.Add(r.w * h_ratio <= r.h * w_ratio)  # type: ignore
        model.Add(r.h * h_ratio <= r.w * w_ratio)  # type: ignore
