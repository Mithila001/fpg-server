from __future__ import annotations

from typing import Any

from .types import PostProcessedLayout
from .validators import normalize_solution_rooms
from .wall_generator import generate_unique_wall_segments


def build_post_processed_layout(
    solution: list[dict[str, Any]],
    tolerance: float = 1e-6,
) -> PostProcessedLayout:
    """Convert solver solution rooms into frontend-ready walls + room labels."""
    normalized_rooms = normalize_solution_rooms(solution)
    walls = generate_unique_wall_segments(normalized_rooms, tolerance=tolerance)

    rooms = [
        {
            "name": room["name"],
            "type": room["type"],
            "center": {
                "x": (room["x"] + room["x_end"]) / 2.0,
                "y": (room["y"] + room["y_end"]) / 2.0,
            },
        }
        for room in normalized_rooms
    ]

    return {
        "walls": walls,
        "rooms": rooms,
    }
