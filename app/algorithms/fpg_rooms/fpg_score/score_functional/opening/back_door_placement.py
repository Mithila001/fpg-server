from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ._helpers import clamp_0_25, normalize_str, opening_on_room_boundary, openings_of_type, room_by_name


_ELIGIBLE_TYPES = {"kitchen", "hallway"}


def evaluate_back_door_placement(
    rooms: Sequence[Mapping[str, Any]],
    openings: Sequence[Mapping[str, Any]],
) -> Tuple[float, Dict[str, Any]]:
    back_doors = openings_of_type(openings, "backDoor")
    rooms_index = room_by_name(rooms)

    has_back_door = len(back_doors) > 0
    single_back_door = len(back_doors) == 1

    eligible_count = 0
    valid_boundary_count = 0
    for opening in back_doors:
        room_name = normalize_str(opening.get("room_name"))
        room = rooms_index.get(room_name)
        if room is None:
            continue
        room_type = normalize_str(room.get("type"))
        if room_type in _ELIGIBLE_TYPES:
            eligible_count += 1
        if opening_on_room_boundary(opening, room):
            valid_boundary_count += 1

    all_in_eligible_rooms = has_back_door and eligible_count == len(back_doors)
    all_boundary_valid = has_back_door and valid_boundary_count == len(back_doors)

    checks = [
        ("has_back_door", has_back_door),
        ("single_back_door", single_back_door),
        ("eligible_room_type", all_in_eligible_rooms),
        ("back_door_boundary_valid", all_boundary_valid),
    ]
    passed = sum(1 for _, ok in checks if ok)
    score = clamp_0_25(25.0 * passed / len(checks))

    diagnostics = {
        "checks": [{"name": name, "passed": ok} for name, ok in checks],
        "back_door_count": len(back_doors),
        "eligible_count": eligible_count,
        "valid_boundary_count": valid_boundary_count,
    }
    return score, diagnostics