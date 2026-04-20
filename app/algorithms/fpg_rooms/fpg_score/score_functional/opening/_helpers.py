from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence


def normalize_str(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_opening_type(value: Any) -> str:
    normalized = normalize_str(value)
    aliases = {
        "maindoor": "maindoor",
        "main_door": "maindoor",
        "backdoor": "backdoor",
        "back_door": "backdoor",
        "internaldoor": "internaldoor",
        "internal_door": "internaldoor",
        "window": "window",
    }
    return aliases.get(normalized, normalized)


def room_by_name(rooms: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {normalize_str(room.get("name")): room for room in rooms}


def openings_of_type(
    openings: Sequence[Mapping[str, Any]],
    opening_type: str,
) -> list[Mapping[str, Any]]:
    expected = normalize_opening_type(opening_type)
    return [
        opening
        for opening in openings
        if normalize_opening_type(opening.get("opening_type")) == expected
    ]


def opening_on_room_boundary(
    opening: Mapping[str, Any],
    room: Mapping[str, Any],
    tolerance: float = 1e-6,
) -> bool:
    side = normalize_str(opening.get("side"))
    if side not in {"south", "east", "north", "west"}:
        return False

    try:
        x1 = float(opening["x1"])
        y1 = float(opening["y1"])
        x2 = float(opening["x2"])
        y2 = float(opening["y2"])
        rx = float(room["x"])
        ry = float(room["y"])
        rx_end = float(room["x_end"])
        ry_end = float(room["y_end"])
    except (KeyError, TypeError, ValueError):
        return False

    x_min = min(x1, x2)
    x_max = max(x1, x2)
    y_min = min(y1, y2)
    y_max = max(y1, y2)

    if side == "south":
        return (
            abs(y1 - ry) <= tolerance
            and abs(y2 - ry) <= tolerance
            and x_min >= rx - tolerance
            and x_max <= rx_end + tolerance
        )
    if side == "north":
        return (
            abs(y1 - ry_end) <= tolerance
            and abs(y2 - ry_end) <= tolerance
            and x_min >= rx - tolerance
            and x_max <= rx_end + tolerance
        )
    if side == "west":
        return (
            abs(x1 - rx) <= tolerance
            and abs(x2 - rx) <= tolerance
            and y_min >= ry - tolerance
            and y_max <= ry_end + tolerance
        )
    return (
        abs(x1 - rx_end) <= tolerance
        and abs(x2 - rx_end) <= tolerance
        and y_min >= ry - tolerance
        and y_max <= ry_end + tolerance
    )


def clamp_0_25(value: float) -> float:
    return max(0.0, min(25.0, float(value)))