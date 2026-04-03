from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SeedLayoutContext:
    by_name: dict[str, dict[str, Any]]
    left_line: int
    right_line: int
    back_line: int
    front_line: int
    side_facing_names: dict[str, set[str]]


def get_seed_room_bounds(seed: dict[str, Any]) -> tuple[int, int, int, int]:
    sx = int(seed.get("x", 0))
    sy = int(seed.get("y", 0))
    sx_end = int(seed.get("x_end", sx + int(seed.get("w", 0))))
    sy_end = int(seed.get("y_end", sy + int(seed.get("h", 0))))
    return sx, sy, sx_end, sy_end


def axis_overlap_len(a1: int, a2: int, b1: int, b2: int) -> int:
    return max(0, min(a2, b2) - max(a1, b1))


def build_seed_layout_context(seed_layout: list[dict[str, Any]]) -> SeedLayoutContext | None:
    by_name = {
        str(room.get("name")): room
        for room in seed_layout
        if isinstance(room, dict) and room.get("name") is not None
    }
    if not by_name:
        return None

    seed_rooms = list(by_name.values())
    left_line = min(int(room.get("x", 0)) for room in seed_rooms)
    right_line = max(int(room.get("x_end", room.get("x", 0))) for room in seed_rooms)
    back_line = min(int(room.get("y", 0)) for room in seed_rooms)
    front_line = max(int(room.get("y_end", room.get("y", 0))) for room in seed_rooms)

    side_facing_names = {
        "front": {str(room.get("name")) for room in seed_rooms if int(room.get("y_end", 0)) == front_line},
        "back": {str(room.get("name")) for room in seed_rooms if int(room.get("y", 0)) == back_line},
        "left": {str(room.get("name")) for room in seed_rooms if int(room.get("x", 0)) == left_line},
        "right": {str(room.get("name")) for room in seed_rooms if int(room.get("x_end", 0)) == right_line},
    }

    return SeedLayoutContext(
        by_name=by_name,
        left_line=left_line,
        right_line=right_line,
        back_line=back_line,
        front_line=front_line,
        side_facing_names=side_facing_names,
    )
