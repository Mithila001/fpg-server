from typing import Dict, List, Tuple

from app.core.fpg_rooms.config_fpg import MAX_ASPECT_RATIO_HEIGHT, MAX_ASPECT_RATIO_WIDTH

from ...solver_models.room import Room


ROOM_TYPE_ASPECT_RATIO: Dict[str, Tuple[int, int]] = {
    # Use integer pairs to represent max ratios without losing precision.
    # ratio = width / height
    "garage": (2, 5),  # max ratio 2.5
    "veranda": (1, 3),  # max ratio 3.0
}


def add_basic_constraints(model, rooms: List[Room]) -> None:
    """Add no-overlap and aspect-ratio constraints to all rooms."""
    default_h_ratio = int(MAX_ASPECT_RATIO_HEIGHT)
    default_w_ratio = int(MAX_ASPECT_RATIO_WIDTH)

    x_intervals = [r.x_interval for r in rooms]
    y_intervals = [r.y_interval for r in rooms]
    model.AddNoOverlap2D(x_intervals, y_intervals)

    for room in rooms:
        model.Add(room.x + room.w == room.x_end)  # type: ignore
        model.Add(room.y + room.h == room.y_end)  # type: ignore

        if room.type == "hallway":
            continue

        h_ratio, w_ratio = ROOM_TYPE_ASPECT_RATIO.get(
            room.type, (default_h_ratio, default_w_ratio)
        )
        model.Add(room.w * h_ratio <= room.h * w_ratio)  # type: ignore
        model.Add(room.h * h_ratio <= room.w * w_ratio)  # type: ignore
