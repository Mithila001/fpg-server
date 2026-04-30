from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from math import floor
from typing import Any, Mapping, Sequence

from app.algorithms.types import FpgRequirements

ROOM_TYPE_VERANDA = "veranda"
ROOM_TYPE_GARAGE = "garage"
ROOM_TYPE_KITCHEN = "kitchen"
ROOM_TYPE_HALLWAY = "hallway"
ROOM_TYPE_LIVING_ROOM = "livingRoom"
ROOM_TYPE_BATHROOM = "bathroom"
ROOM_TYPE_BEDROOM = "bedroom"
ROOM_TYPE_DINING_ROOM = "diningRoom"


@dataclass(frozen=True)
class OptunaScorePoint:
    name: str
    room_type: str
    x: float
    y: float


@dataclass
class SectionScore:
    score: float
    max_score: float
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def log_critical_graph_scoring(message: str) -> None:
    print(f"[Critical_Graph_Scoring] {message}")


def coerce_position(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        if "x" in value and "y" in value:
            try:
                return float(value["x"]), float(value["y"])
            except (TypeError, ValueError):
                return None

        if "position" in value:
            return coerce_position(value["position"])

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) >= 2:
            try:
                return float(value[0]), float(value[1])
            except (TypeError, ValueError):
                return None

    return None


def build_room_points(
    requirements: FpgRequirements,
    sampled_positions: Mapping[str, Any],
) -> list[OptunaScorePoint]:
    room_points: list[OptunaScorePoint] = []
    for room in requirements.rooms:
        position = coerce_position(sampled_positions.get(room.name))
        if position is None:
            log_critical_graph_scoring(
                f"Missing sampled position for room '{room.name}' ({room.type})"
            )
            continue

        x, y = position
        room_points.append(
            OptunaScorePoint(name=room.name, room_type=room.type, x=x, y=y)
        )

    return room_points


def room_type_counts(room_points: Sequence[OptunaScorePoint]) -> Counter[str]:
    return Counter(point.room_type for point in room_points)


def room_types_by_name(room_points: Sequence[OptunaScorePoint]) -> dict[str, str]:
    return {point.name: point.room_type for point in room_points}


def normalize_section_score(raw_score: float, max_score: float) -> float:
    if max_score <= 0:
        return 0.0
    return max(0.0, min(float(max_score), float(raw_score)))


def cell_to_rect(
    cell_x: int,
    cell_y: int,
    floor_width: float,
    floor_height: float,
) -> tuple[float, float, float, float]:
    cell_width = float(floor_width) / 3.0
    cell_height = float(floor_height) / 3.0
    min_x = (cell_x - 1) * cell_width
    max_x = cell_x * cell_width
    min_y = (cell_y - 1) * cell_height
    max_y = cell_y * cell_height
    return min_x, min_y, max_x, max_y


def point_to_cell(
    x: float,
    y: float,
    floor_width: float,
    floor_height: float,
) -> tuple[int, int]:
    clamped_x = max(0.0, min(float(x), float(floor_width)))
    clamped_y = max(0.0, min(float(y), float(floor_height)))

    safe_width = max(float(floor_width), 1e-9)
    safe_height = max(float(floor_height), 1e-9)
    cell_x = min(3, max(1, int(floor((clamped_x / safe_width) * 3.0)) + 1))
    cell_y = min(3, max(1, int(floor((clamped_y / safe_height) * 3.0)) + 1))
    return cell_x, cell_y