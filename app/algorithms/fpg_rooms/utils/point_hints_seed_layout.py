from __future__ import annotations

from typing import Any

from app.algorithms.fpg_rooms.solver_models.room import Room


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _read_hint_point(hint: dict[str, Any]) -> tuple[int, int] | None:
    try:
        x_raw = hint.get("x")
        y_raw = hint.get("y")
        if x_raw is None or y_raw is None:
            return None

        x = int(x_raw)
        y = int(y_raw)
    except (TypeError, ValueError):
        return None
    return x, y


def _room_key_candidates(room: Room) -> tuple[str, str]:
    return str(room.name).strip().lower(), str(room.type).strip().lower()


def build_seed_layout_from_point_hints(
    rooms: list[Room],
    floor_plan_width: float,
    floor_plan_height: float,
    point_hints: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Convert optional point hints to the existing seed_layout shape.

    Hints are soft initial suggestions only. Unknown/malformed hints are ignored.
    """
    if not point_hints:
        return []

    room_by_name: dict[str, Room] = {}
    room_by_type: dict[str, list[Room]] = {}
    for room in rooms:
        room_name, room_type = _room_key_candidates(room)
        room_by_name[room_name] = room
        room_by_type.setdefault(room_type, []).append(room)

    seeded_room_names: set[str] = set()
    w_int = max(1, int(floor_plan_width))
    h_int = max(1, int(floor_plan_height))
    seed_layout: list[dict[str, Any]] = []

    for hint in point_hints:
        if not isinstance(hint, dict):
            continue

        point = _read_hint_point(hint)
        if point is None:
            continue

        name_key = str(hint.get("name", "")).strip().lower()
        type_key = str(hint.get("type", "")).strip().lower()

        room: Room | None = None
        if name_key:
            room = room_by_name.get(name_key)

        if room is None and type_key:
            for candidate in room_by_type.get(type_key, []):
                if candidate.name not in seeded_room_names:
                    room = candidate
                    break

        if room is None or room.name in seeded_room_names:
            continue

        x, y = point

        max_x = max(0, w_int - room.min_w)
        max_y = max(0, h_int - room.min_h)
        sx = _clamp(x, 0, max_x)
        sy = _clamp(y, 0, max_y)

        sw = _clamp(room.min_w, room.min_w, room.max_w)
        sh = _clamp(room.min_h, room.min_h, room.max_h)

        seed_layout.append(
            {
                "name": room.name,
                "type": room.type,
                "x": sx,
                "y": sy,
                "w": sw,
                "h": sh,
                "x_end": sx + sw,
                "y_end": sy + sh,
            }
        )
        seeded_room_names.add(room.name)

    return seed_layout
