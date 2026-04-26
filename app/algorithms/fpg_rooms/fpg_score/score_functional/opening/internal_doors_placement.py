from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ._helpers import (
    clamp_0_25,
    normalize_str,
    opening_on_room_boundary,
    openings_of_type,
    room_by_name,
)


def evaluate_internal_doors_placement(
    rooms: Sequence[Mapping[str, Any]],
    openings: Sequence[Mapping[str, Any]],
) -> Tuple[float, Dict[str, Any]]:
    internal_doors = openings_of_type(openings, "internalDoor")
    rooms_index = room_by_name(rooms)

    has_internal_doors = len(internal_doors) > 0

    with_connected_room_count = 0
    connected_room_exists_count = 0
    valid_boundary_count = 0
    seen_pairs: set[tuple[str, str]] = set()
    duplicate_pair_count = 0

    for opening in internal_doors:
        room_name = normalize_str(opening.get("room_name"))
        connected_room_name = normalize_str(opening.get("connected_room_name"))
        room = rooms_index.get(room_name)

        if connected_room_name:
            with_connected_room_count += 1
        if connected_room_name in rooms_index:
            connected_room_exists_count += 1
        if room is not None and opening_on_room_boundary(opening, room):
            valid_boundary_count += 1

        if room_name and connected_room_name:
            pair = tuple(sorted((room_name, connected_room_name)))
            if pair in seen_pairs:
                duplicate_pair_count += 1
            else:
                seen_pairs.add((pair[0], pair[1]))

    all_have_connected_room = has_internal_doors and with_connected_room_count == len(
        internal_doors
    )
    all_connected_exist = has_internal_doors and connected_room_exists_count == len(
        internal_doors
    )
    all_boundary_valid = has_internal_doors and valid_boundary_count == len(
        internal_doors
    )
    no_duplicate_pairs = duplicate_pair_count == 0

    checks = [
        ("has_internal_doors", has_internal_doors),
        ("connected_room_present", all_have_connected_room),
        ("connected_room_exists", all_connected_exist),
        ("internal_door_boundary_valid", all_boundary_valid),
        ("no_duplicate_pairs", no_duplicate_pairs),
    ]
    passed = sum(1 for _, ok in checks if ok)
    score = clamp_0_25(25.0 * passed / len(checks))

    diagnostics = {
        "checks": [{"name": name, "passed": ok} for name, ok in checks],
        "internal_door_count": len(internal_doors),
        "connected_room_count": with_connected_room_count,
        "connected_room_exists_count": connected_room_exists_count,
        "valid_boundary_count": valid_boundary_count,
        "duplicate_pair_count": duplicate_pair_count,
    }
    return score, diagnostics
