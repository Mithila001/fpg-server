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

    target_area = total_min_area
    start_width = 100 if max_floor_width >= 100 else max_floor_width
    min_width_float = max(
        float(start_width),
        math.sqrt(target_area),
        target_area / float(max_floor_height),
    )
    max_width_float = min(
        float(max_floor_width),
        math.sqrt(2.0 * target_area),
    )

    found_width = 0
    found_height = 0
    if min_width_float <= max_width_float:
        search_start = int(math.ceil(min_width_float))
        search_end = int(math.floor(max_width_float))

        # First try to find a floor size close to the preferred 1:1.5 aspect ratio.
        preferred_ratio = 1.5
        preferred_tolerance = 0.05
        best_preferred = None
        best_distance = float("inf")

        for candidate_width in range(search_start, search_end + 1):
            candidate_height = int(math.ceil(target_area / float(candidate_width)))
            if candidate_height > max_floor_height:
                continue
            candidate_ratio = float(candidate_width) / float(candidate_height)
            if candidate_ratio < 1.0 or candidate_ratio > 2.0:
                continue
            if candidate_width * candidate_height < target_area:
                continue

            ratio_distance = abs(candidate_ratio - preferred_ratio)
            if ratio_distance < best_distance:
                best_distance = ratio_distance
                best_preferred = (candidate_width, candidate_height)

        if best_preferred is not None and best_distance <= preferred_tolerance:
            found_width, found_height = best_preferred
        else:
            for candidate_width in range(search_start, search_end + 1):
                candidate_height = int(math.ceil(target_area / float(candidate_width)))
                if candidate_height > max_floor_height:
                    continue
                candidate_ratio = float(candidate_width) / float(candidate_height)
                if candidate_ratio < 1.0 or candidate_ratio > 2.0:
                    continue
                if candidate_width * candidate_height < target_area:
                    continue
                found_width = candidate_width
                found_height = candidate_height
                break

    if found_width <= 0 or found_height <= 0:
        return FloorBoundsResult(
            feasible=False,
            reason=(
                "Unable to find floor dimensions for the total min area "
                f"({total_min_area:.2f}) within max bounds {max_floor_width}x{max_floor_height} "
                "and aspect ratio 1:1 to 1:2."
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