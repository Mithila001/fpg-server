from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.core.fpg_rooms.config_score import (
    SCORE_ENVELOPE_APPLY_SIDES,
    SCORE_ENVELOPE_EXCLUDE_TYPES,
    SCORE_ENVELOPE_MAX_GAP,
    SCORE_ENVELOPE_MIN_GAP,
)

from ..utils import strict_axis_overlap


def validate_envelope_staircase_bounds(
    solution: Sequence[Dict[str, Any]],
    min_gap: int = SCORE_ENVELOPE_MIN_GAP,
    max_gap: int = SCORE_ENVELOPE_MAX_GAP,
    exclude_types: Sequence[str] | None = None,
    apply_sides: Sequence[str] | None = None,
) -> List[str]:
    """Validate exterior-room recess depth bounds for selected envelope sides.

    A room is considered exterior on a side when no other non-excluded room lies
    further outward on that side while overlapping on the orthogonal axis.
    """
    violations: List[str] = []
    if not solution:
        return violations

    min_gap = max(1, int(min_gap))
    max_gap = max(min_gap, int(max_gap))

    excluded = {str(t).lower() for t in (exclude_types or SCORE_ENVELOPE_EXCLUDE_TYPES)}
    sides = {
        str(side).lower() for side in (apply_sides or SCORE_ENVELOPE_APPLY_SIDES)
    }
    sides = sides.intersection({"left", "right", "top", "bottom"})
    if not sides:
        return violations

    eligible = [room for room in solution if str(room.get("type", "")).lower() not in excluded]
    if len(eligible) < 2:
        return violations

    left_outer = min(int(room["x"]) for room in eligible)
    right_outer = max(int(room["x_end"]) for room in eligible)
    bottom_outer = min(int(room["y"]) for room in eligible)
    top_outer = max(int(room["y_end"]) for room in eligible)

    for room in eligible:
        room_name = str(room.get("name", "<unknown>"))
        room_x = int(room["x"])
        room_x_end = int(room["x_end"])
        room_y = int(room["y"])
        room_y_end = int(room["y_end"])

        if "left" in sides:
            has_left_blocker = any(
                int(other["x"]) < room_x
                and strict_axis_overlap(
                    room_y,
                    room_y_end,
                    int(other["y"]),
                    int(other["y_end"]),
                )
                for other in eligible
                if other is not room
            )
            if not has_left_blocker:
                gap = room_x - left_outer
                if gap > 0 and not (min_gap <= gap <= max_gap):
                    violations.append(
                        f"Envelope left-gap violation for '{room_name}': {gap} not in [{min_gap}, {max_gap}]"
                    )

        if "right" in sides:
            has_right_blocker = any(
                int(other["x_end"]) > room_x_end
                and strict_axis_overlap(
                    room_y,
                    room_y_end,
                    int(other["y"]),
                    int(other["y_end"]),
                )
                for other in eligible
                if other is not room
            )
            if not has_right_blocker:
                gap = right_outer - room_x_end
                if gap > 0 and not (min_gap <= gap <= max_gap):
                    violations.append(
                        f"Envelope right-gap violation for '{room_name}': {gap} not in [{min_gap}, {max_gap}]"
                    )

        if "bottom" in sides:
            has_bottom_blocker = any(
                int(other["y"]) < room_y
                and strict_axis_overlap(
                    room_x,
                    room_x_end,
                    int(other["x"]),
                    int(other["x_end"]),
                )
                for other in eligible
                if other is not room
            )
            if not has_bottom_blocker:
                gap = room_y - bottom_outer
                if gap > 0 and not (min_gap <= gap <= max_gap):
                    violations.append(
                        f"Envelope bottom-gap violation for '{room_name}': {gap} not in [{min_gap}, {max_gap}]"
                    )

        if "top" in sides:
            has_top_blocker = any(
                int(other["y_end"]) > room_y_end
                and strict_axis_overlap(
                    room_x,
                    room_x_end,
                    int(other["x"]),
                    int(other["x_end"]),
                )
                for other in eligible
                if other is not room
            )
            if not has_top_blocker:
                gap = top_outer - room_y_end
                if gap > 0 and not (min_gap <= gap <= max_gap):
                    violations.append(
                        f"Envelope top-gap violation for '{room_name}': {gap} not in [{min_gap}, {max_gap}]"
                    )

    return violations
