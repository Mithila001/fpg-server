from __future__ import annotations

from typing import Any, Dict


def interval_overlap_len(a1: int, a2: int, b1: int, b2: int) -> int:
    return min(a2, b2) - max(a1, b1)


def touches_with_min_overlap(
    room_a: Dict[str, Any],
    room_b: Dict[str, Any],
    min_overlap: int,
) -> bool:
    # Vertical edge touch: left/right faces touching with y-overlap.
    if room_a["x_end"] == room_b["x"] or room_a["x"] == room_b["x_end"]:
        return (
            interval_overlap_len(
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
            interval_overlap_len(
                int(room_a["x"]),
                int(room_a["x_end"]),
                int(room_b["x"]),
                int(room_b["x_end"]),
            )
            >= min_overlap
        )

    return False


def strict_axis_overlap(
    a1: int,
    a2: int,
    b1: int,
    b2: int,
) -> bool:
    return interval_overlap_len(a1, a2, b1, b2) > 0
