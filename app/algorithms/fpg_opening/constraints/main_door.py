from __future__ import annotations

from app.algorithms.fpg_opening.types.opening import NormalizedRoom, OpeningPayload


def _wall_length(room: NormalizedRoom, side: str) -> float:
    if side in {"south", "north"}:
        return room["x_end"] - room["x"]
    return room["y_end"] - room["y"]


def _opening_segment_for_side(
    room: NormalizedRoom,
    side: str,
    preferred_door_length: float,
) -> tuple[float, float, float, float]:
    if side in {"south", "north"}:
        start = room["x"]
        end = room["x_end"]
        wall_y = room["y"] if side == "south" else room["y_end"]

        wall_length = end - start
        door_length = min(preferred_door_length, wall_length)
        mid = (start + end) / 2.0
        x1 = mid - (door_length / 2.0)
        x2 = mid + (door_length / 2.0)
        return x1, wall_y, x2, wall_y

    start = room["y"]
    end = room["y_end"]
    wall_x = room["x"] if side == "west" else room["x_end"]

    wall_length = end - start
    door_length = min(preferred_door_length, wall_length)
    mid = (start + end) / 2.0
    y1 = mid - (door_length / 2.0)
    y2 = mid + (door_length / 2.0)
    return wall_x, y1, wall_x, y2


def select_main_door(
    room: NormalizedRoom,
    exterior_sides: set[str],
    side_priority: tuple[str, ...] = ("south", "east", "north", "west"),
    preferred_door_length: float = 8.0,
) -> OpeningPayload | None:
    if not exterior_sides:
        return None

    selected_side = None
    for side in side_priority:
        if side in exterior_sides:
            selected_side = side
            break

    if selected_side is None:
        # Fallback for unexpected side labels.
        selected_side = sorted(exterior_sides)[0]

    x1, y1, x2, y2 = _opening_segment_for_side(room, selected_side, preferred_door_length)

    return {
        "room_name": room["name"],
        "room_type": room["type"],
        "opening_type": "mainDoor",
        "side": selected_side,  # type: ignore[typeddict-item]
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
    }
