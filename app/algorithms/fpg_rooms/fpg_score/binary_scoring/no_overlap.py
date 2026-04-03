from __future__ import annotations

from typing import Any, Dict, List, Sequence


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
