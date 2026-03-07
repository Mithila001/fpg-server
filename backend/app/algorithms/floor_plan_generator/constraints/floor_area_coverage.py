from ortools.sat.python import cp_model
from typing import List
from ..models.room import Room


def add_minimum_area_coverage(
    model: cp_model.CpModel,
    rooms: List[Room],
    floor_width: int,
    floor_height: int,
    min_coverage: float = 0.5,
):
    """Enforce that the combined room area covers at least min_coverage of the floor."""
    total_floor_area = floor_width * floor_height
    min_required_area = int(total_floor_area * min_coverage)

    room_areas = [r.area for r in rooms]
    model.Add(sum(room_areas) >= min_required_area)  # type: ignore
