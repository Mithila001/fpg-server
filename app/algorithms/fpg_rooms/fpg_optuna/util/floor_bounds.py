from __future__ import annotations

from dataclasses import dataclass
import math

from app.algorithms.fpg_rooms.types.room import FpgRequirements
from app.core.fpg_rooms.config_fpg import (
    HALLWAY_GENERATOR_MIN_HEIGHT,
    HALLWAY_GENERATOR_MIN_WIDTH,
    LIVING_ROOM_MIN_HEIGHT,
    LIVING_ROOM_MIN_WIDTH,
    MIN_FLOOR_AREA_BUFFER,
)


@dataclass
class FloorBoundsResult:
    feasible: bool
    reason: str
    min_floor_width: int
    min_floor_height: int
    max_floor_width: int
    max_floor_height: int
    total_min_area: float
    additional_min_area: float
    required_floor_area: float


def _room_min_area(requirements: FpgRequirements) -> float:
    total_min_area = 0.0
    for room in requirements.rooms:
        total_min_area += float(room.min_w) * float(room.min_h)

    total_min_area += float(LIVING_ROOM_MIN_WIDTH) * float(LIVING_ROOM_MIN_HEIGHT)

    hallway_count = max(0, int(getattr(requirements.config, "hallway_count", 0)))
    if hallway_count > 0:
        hallway_area = float(HALLWAY_GENERATOR_MIN_WIDTH) * float(HALLWAY_GENERATOR_MIN_HEIGHT)
        total_min_area += float(hallway_count) * hallway_area

    return total_min_area


def _room_min_extents(requirements: FpgRequirements) -> tuple[int, int]:
    min_width = 1
    min_height = 1

    for room in requirements.rooms:
        min_width = max(min_width, int(room.min_w))
        min_height = max(min_height, int(room.min_h))

    min_width = max(min_width, int(LIVING_ROOM_MIN_WIDTH))
    min_height = max(min_height, int(LIVING_ROOM_MIN_HEIGHT))

    hallway_count = max(0, int(getattr(requirements.config, "hallway_count", 0)))
    if hallway_count > 0:
        min_width = max(min_width, int(HALLWAY_GENERATOR_MIN_WIDTH))
        min_height = max(min_height, int(HALLWAY_GENERATOR_MIN_HEIGHT))

    print(f"[DEBUG] Final Min Extents Required: {min_width}x{min_height}")
    return min_width, min_height


def calculate_floor_bounds(
    requirements: FpgRequirements,
) -> FloorBoundsResult:
    max_floor_width = max(1, int(requirements.config.floor_plan_width))
    max_floor_height = max(1, int(requirements.config.floor_plan_height))
    max_floor_area = float(max_floor_width) * float(max_floor_height)

    total_min_area = _room_min_area(requirements)
    if total_min_area > max_floor_area:
        return FloorBoundsResult(
            feasible=False,
            reason=(
                "Insufficient floor area for the trial requirements "
                f"({total_min_area:.2f} > {max_floor_area:.2f})."
            ),
            min_floor_width=0,
            min_floor_height=0,
            max_floor_width=max_floor_width,
            max_floor_height=max_floor_height,
            total_min_area=total_min_area,
            additional_min_area=0.0,
            required_floor_area=total_min_area,
        )

    available_area = max_floor_area - total_min_area
    additional_min_area = min(available_area, float(MIN_FLOOR_AREA_BUFFER))
    required_floor_area = total_min_area + additional_min_area

    aspect_ratio = (
        float(max_floor_width) / float(max_floor_height)
        if max_floor_height > 0
        else 1.0
    )
    if not math.isfinite(aspect_ratio) or aspect_ratio <= 0.0:
        aspect_ratio = 1.0

    room_min_width, room_min_height = _room_min_extents(requirements)
    min_floor_height = max(1, room_min_height)

    found_width = 0
    found_height = 0
    for candidate_height in range(min_floor_height, max_floor_height + 1):
        width_from_area = int(math.ceil(required_floor_area / candidate_height))
        width_from_aspect = int(math.ceil(aspect_ratio * candidate_height))
        candidate_width = max(room_min_width, width_from_area, width_from_aspect)
        if candidate_width > max_floor_width:
            continue
        if candidate_width * candidate_height < required_floor_area:
            continue
        found_width = candidate_width
        found_height = candidate_height
        break

    if found_width <= 0 or found_height <= 0:
        return FloorBoundsResult(
            feasible=False,
            reason=(
                "Required floor bounds exceed max floor bounds "
                f"(area={required_floor_area:.2f}, max={max_floor_width}x{max_floor_height}, "
                f"room_min={room_min_width}x{room_min_height}, aspect={aspect_ratio:.4f})."
            ),
            min_floor_width=0,
            min_floor_height=0,
            max_floor_width=max_floor_width,
            max_floor_height=max_floor_height,
            total_min_area=total_min_area,
            additional_min_area=additional_min_area,
            required_floor_area=required_floor_area,
        )

    return FloorBoundsResult(
        feasible=True,
        reason="",
        min_floor_width=found_width,
        min_floor_height=found_height,
        max_floor_width=max_floor_width,
        max_floor_height=max_floor_height,
        total_min_area=total_min_area,
        additional_min_area=additional_min_area,
        required_floor_area=required_floor_area,
    )