from __future__ import annotations

from typing import Any

from app.algorithms.fpg_opening.types.opening import NormalizedRoom


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise ValueError(f"Expected numeric value, got {type(value)}")


def _overlap_length(a1: float, a2: float, b1: float, b2: float) -> float:
    return min(a2, b2) - max(a1, b1)


def normalize_rooms(room_items: list[dict[str, Any]]) -> list[NormalizedRoom]:
    normalized: list[NormalizedRoom] = []

    for index, room in enumerate(room_items):
        try:
            x = _to_float(room["x"])
            y = _to_float(room["y"])

            raw_x_end = room.get("x_end")
            raw_y_end = room.get("y_end")
            raw_w = room.get("w")
            raw_h = room.get("h")

            if raw_x_end is None:
                if raw_w is None:
                    raise ValueError("Missing w/x_end")
                x_end = x + _to_float(raw_w)
            else:
                x_end = _to_float(raw_x_end)

            if raw_y_end is None:
                if raw_h is None:
                    raise ValueError("Missing h/y_end")
                y_end = y + _to_float(raw_h)
            else:
                y_end = _to_float(raw_y_end)

            if x_end <= x or y_end <= y:
                raise ValueError("Non-positive room bounds")

            normalized.append(
                {
                    "name": str(room.get("name") or f"room_{index}"),
                    "type": str(room.get("type") or ""),
                    "x": x,
                    "y": y,
                    "x_end": x_end,
                    "y_end": y_end,
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid room entry at index {index}: {exc}") from exc

    return normalized


def is_room_type(room: NormalizedRoom, room_type: str) -> bool:
    return room["type"].strip().lower() == room_type.strip().lower()


def get_exterior_sides(
    target_room: NormalizedRoom,
    all_rooms: list[NormalizedRoom],
    tolerance: float = 1e-6,
) -> set[str]:
    x = target_room["x"]
    y = target_room["y"]
    x_end = target_room["x_end"]
    y_end = target_room["y_end"]

    blocked = {"south": False, "east": False, "north": False, "west": False}

    for other in all_rooms:
        if other["name"] == target_room["name"]:
            continue

        overlap_y = _overlap_length(y, y_end, other["y"], other["y_end"])
        overlap_x = _overlap_length(x, x_end, other["x"], other["x_end"])

        if overlap_y > tolerance:
            if abs(other["x_end"] - x) <= tolerance:
                blocked["west"] = True
            if abs(other["x"] - x_end) <= tolerance:
                blocked["east"] = True

        if overlap_x > tolerance:
            if abs(other["y_end"] - y) <= tolerance:
                blocked["south"] = True
            if abs(other["y"] - y_end) <= tolerance:
                blocked["north"] = True

    return {side for side, is_blocked in blocked.items() if not is_blocked}
