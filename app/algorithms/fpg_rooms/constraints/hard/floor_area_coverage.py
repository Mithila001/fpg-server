from typing import List

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import MIN_COVERAGE

from ...solver_models.room import Room


def add_minimum_area_coverage(
    model: cp_model.CpModel,
    rooms: List[Room],
    floor_width: float,
    floor_height: float,
    min_coverage: float = MIN_COVERAGE,
) -> None:
    """Enforce minimum area coverage of the floor by all rooms."""
    total_floor_area = int(floor_width * floor_height)
    min_required_area = int(total_floor_area * min_coverage)

    room_areas = [room.area for room in rooms]
    model.Add(sum(room_areas) >= min_required_area)  # type: ignore
