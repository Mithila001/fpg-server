from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ._helpers import clamp_0_25, normalize_str, opening_on_room_boundary, openings_of_type, room_by_name


def evaluate_main_door_to_outside(
    rooms: Sequence[Mapping[str, Any]],
    openings: Sequence[Mapping[str, Any]],
) -> Tuple[float, Dict[str, Any]]:
    main_doors = openings_of_type(openings, "mainDoor")
    rooms_index = room_by_name(rooms)

    living_room_names = {
        normalize_str(room.get("name"))
        for room in rooms
        if normalize_str(room.get("type")) == "livingroom"
    }

    has_main_door = len(main_doors) > 0

    valid_boundary_count = 0
    for opening in main_doors:
        room_name = normalize_str(opening.get("room_name"))
        room = rooms_index.get(room_name)
        if room is not None and opening_on_room_boundary(opening, room):
            valid_boundary_count += 1

    all_main_doors_valid = has_main_door and valid_boundary_count == len(main_doors)

    rooms_with_main_door = {
        normalize_str(opening.get("room_name"))
        for opening in main_doors
    }
    living_coverage_ok = bool(living_room_names) and living_room_names.issubset(rooms_with_main_door)

    checks = [
        ("has_main_door", has_main_door),
        ("main_door_boundary_valid", all_main_doors_valid),
        ("living_room_coverage", living_coverage_ok),
    ]
    passed = sum(1 for _, ok in checks if ok)
    score = clamp_0_25(25.0 * passed / len(checks))

    diagnostics = {
        "checks": [{"name": name, "passed": ok} for name, ok in checks],
        "main_door_count": len(main_doors),
        "living_room_count": len(living_room_names),
        "rooms_with_main_door": sorted(rooms_with_main_door),
        "valid_boundary_count": valid_boundary_count,
    }
    return score, diagnostics