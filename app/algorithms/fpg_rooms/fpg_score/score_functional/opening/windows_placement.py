from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ._helpers import clamp_0_25, normalize_str, opening_on_room_boundary, openings_of_type, room_by_name


_WINDOW_ELIGIBLE_TYPES = {"bedroom", "livingroom", "kitchen"}


def evaluate_windows_placement(
    rooms: Sequence[Mapping[str, Any]],
    openings: Sequence[Mapping[str, Any]],
) -> Tuple[float, Dict[str, Any]]:
    windows = openings_of_type(openings, "window")
    rooms_index = room_by_name(rooms)

    eligible_rooms = {
        normalize_str(room.get("name"))
        for room in rooms
        if normalize_str(room.get("type")) in _WINDOW_ELIGIBLE_TYPES
    }

    has_windows = len(windows) > 0

    eligible_room_count = 0
    valid_boundary_count = 0
    rooms_with_window: set[str] = set()

    for opening in windows:
        room_name = normalize_str(opening.get("room_name"))
        room = rooms_index.get(room_name)
        if room is None:
            continue

        room_type = normalize_str(room.get("type"))
        if room_type in _WINDOW_ELIGIBLE_TYPES:
            eligible_room_count += 1
            rooms_with_window.add(room_name)
        if opening_on_room_boundary(opening, room):
            valid_boundary_count += 1

    windows_on_eligible_rooms = has_windows and eligible_room_count == len(windows)
    all_boundary_valid = has_windows and valid_boundary_count == len(windows)
    eligible_coverage_ok = bool(eligible_rooms) and eligible_rooms.issubset(rooms_with_window)

    checks = [
        ("has_windows", has_windows),
        ("windows_on_eligible_rooms", windows_on_eligible_rooms),
        ("window_boundary_valid", all_boundary_valid),
        ("eligible_room_window_coverage", eligible_coverage_ok),
    ]
    passed = sum(1 for _, ok in checks if ok)
    score = clamp_0_25(25.0 * passed / len(checks))

    diagnostics = {
        "checks": [{"name": name, "passed": ok} for name, ok in checks],
        "window_count": len(windows),
        "eligible_room_count": len(eligible_rooms),
        "rooms_with_window": sorted(rooms_with_window),
        "valid_boundary_count": valid_boundary_count,
    }
    return score, diagnostics