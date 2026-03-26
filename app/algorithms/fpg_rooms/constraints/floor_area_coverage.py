from ortools.sat.python import cp_model
from typing import List
from ..solver_models.room import Room
from app.core.fpg_rooms.config_fpg import MIN_COVERAGE


def add_minimum_area_coverage(
    model: cp_model.CpModel,
    rooms: List[Room],
    floor_width: float,
    floor_height: float,
    min_coverage: float = MIN_COVERAGE,
):
    """Enforce that the combined room area covers at least min_coverage of the floor.

    ``floor_width``/``floor_height`` are floats to keep the API flexible, but the
    solver works with integers so we convert them when computing the total area.
    """
    total_floor_area = int(floor_width * floor_height)
    min_required_area = int(total_floor_area * min_coverage)

    room_areas = [r.area for r in rooms]
    model.Add(sum(room_areas) >= min_required_area)  # type: ignore
