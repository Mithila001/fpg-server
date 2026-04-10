from __future__ import annotations

from typing import Any, Dict, List, Sequence


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
