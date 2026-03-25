from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.core.config_score import (
    SCORE_ENVELOPE_APPLY_SIDES,
    SCORE_ENVELOPE_EXCLUDE_TYPES,
    SCORE_ENVELOPE_MAX_GAP,
    SCORE_ENVELOPE_MIN_GAP,
    SCORE_VALIDATION_MIN_OVERLAP,
)


def _interval_overlap_len(a1: int, a2: int, b1: int, b2: int) -> int:
    return min(a2, b2) - max(a1, b1)


def _touches_with_min_overlap(
    room_a: Dict[str, Any],
    room_b: Dict[str, Any],
    min_overlap: int,
) -> bool:
    # Vertical edge touch: left/right faces touching with y-overlap.
    if room_a["x_end"] == room_b["x"] or room_a["x"] == room_b["x_end"]:
        return (
            _interval_overlap_len(
                int(room_a["y"]),
                int(room_a["y_end"]),
                int(room_b["y"]),
                int(room_b["y_end"]),
            )
            >= min_overlap
        )

    # Horizontal edge touch: top/bottom faces touching with x-overlap.
    if room_a["y_end"] == room_b["y"] or room_a["y"] == room_b["y_end"]:
        return (
            _interval_overlap_len(
                int(room_a["x"]),
                int(room_a["x_end"]),
                int(room_b["x"]),
                int(room_b["x_end"]),
            )
            >= min_overlap
        )

    return False


def validate_room_geometry(
    solution: Sequence[Dict[str, Any]],
    floor_width: float,
    floor_height: float,
) -> List[str]:
    """Validate room dimensions, coordinate consistency, and floor bounds."""
    violations: List[str] = []
    max_x = int(floor_width)
    max_y = int(floor_height)

    for room in solution:
        name = str(room.get("name", "<unknown>"))
        x = int(room.get("x", 0))
        y = int(room.get("y", 0))
        w = int(room.get("w", 0))
        h = int(room.get("h", 0))
        x_end = int(room.get("x_end", 0))
        y_end = int(room.get("y_end", 0))

        if w <= 0 or h <= 0:
            violations.append(f"Room '{name}' has non-positive dimensions: w={w}, h={h}")

        if x_end != x + w or y_end != y + h:
            violations.append(
                f"Room '{name}' has inconsistent coordinates: "
                f"(x_end={x_end}, y_end={y_end}) != (x+w={x + w}, y+h={y + h})"
            )

        if x < 0 or y < 0 or x_end > max_x or y_end > max_y:
            violations.append(
                f"Room '{name}' is out of floor bounds: "
                f"[{x},{y}] -> [{x_end},{y_end}] on floor {max_x}x{max_y}"
            )

    return violations


def validate_no_overlap(solution: Sequence[Dict[str, Any]]) -> List[str]:
    """Validate that no two rooms overlap with positive area."""
    violations: List[str] = []

    for i, room_a in enumerate(solution):
        for j in range(i + 1, len(solution)):
            room_b = solution[j]

            x_overlap = min(int(room_a["x_end"]), int(room_b["x_end"])) - max(
                int(room_a["x"]), int(room_b["x"])
            )
            y_overlap = min(int(room_a["y_end"]), int(room_b["y_end"])) - max(
                int(room_a["y"]), int(room_b["y"])
            )

            if x_overlap > 0 and y_overlap > 0:
                violations.append(
                    f"Rooms '{room_a['name']}' and '{room_b['name']}' overlap "
                    f"(dx={x_overlap}, dy={y_overlap})"
                )

    return violations


def validate_adjacency_relations(
    solution: Sequence[Dict[str, Any]],
    relation_constraints: Sequence[Any],
    min_overlap: int = SCORE_VALIDATION_MIN_OVERLAP,
) -> List[str]:
    """Validate hard adjacency relations against solved rectangles.

    Semantics mirror constraint code: for each rule attached to room_type,
    each required type in related_room must be satisfied independently
    (AND across required types, OR across matching candidates per type).
    """
    violations: List[str] = []

    rooms_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for room in solution:
        rooms_by_type.setdefault(str(room["type"]), []).append(room)

    for room in solution:
        room_type = str(room["type"])
        room_name = str(room["name"])

        matching_rules = [
            r
            for r in relation_constraints
            if getattr(r, "room_type", None) == room_type
            or (isinstance(r, dict) and r.get("room_type") == room_type)
        ]
        if not matching_rules:
            continue

        for rule in matching_rules:
            related = getattr(rule, "related_room", None)
            if related is None and isinstance(rule, dict):
                related = rule.get("related_room")

            related_types = related or []
            for required_type in related_types:
                candidates = [
                    r
                    for r in rooms_by_type.get(str(required_type), [])
                    if str(r["name"]) != room_name
                ]

                if not candidates:
                    violations.append(
                        f"Adjacency rule unsatisfied for '{room_name}' ({room_type}): "
                        f"no candidate room of type '{required_type}'"
                    )
                    continue

                has_touch = any(
                    _touches_with_min_overlap(room, candidate, min_overlap)
                    for candidate in candidates
                )
                if not has_touch:
                    violations.append(
                        f"Adjacency rule unsatisfied for '{room_name}' ({room_type}): "
                        f"must touch at least one room of type '{required_type}'"
                    )

    return violations


def _strict_axis_overlap(
    a1: int,
    a2: int,
    b1: int,
    b2: int,
) -> bool:
    return min(a2, b2) - max(a1, b1) > 0


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
                and _strict_axis_overlap(
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
                and _strict_axis_overlap(
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
                and _strict_axis_overlap(
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
                and _strict_axis_overlap(
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
