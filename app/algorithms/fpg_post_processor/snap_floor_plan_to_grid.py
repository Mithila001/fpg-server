import os
from datetime import datetime
import matplotlib.pyplot as plt
from dataclasses import dataclass, replace
from typing import Tuple, Sequence

from app.algorithms.types.domain import ProcessedRoomData
from test.plotters.plot_grid_snapping import plot_post_process  # Import Sequence


def calculate_polygon_area(vertices: Sequence[Tuple[float, float]]) -> float:
    """
    Calculates area using Sequence to allow list[tuple[int, int]]
    to be passed in safely.
    """
    n = len(vertices)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        # Even if passed as ints, math operations will treat them as floats
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0


def snap_floor_plan_to_grid(
    processed_floor_plan: list[ProcessedRoomData],
) -> list[ProcessedRoomData]:
    snapped_plan: list[ProcessedRoomData] = []

    for room in processed_floor_plan:
        # Explicitly casting to float in the tuple to match ProcessedRoomData.vertices
        snapped_vertices: list[Tuple[float, float]] = [
            (float(round(vx)), float(round(vy))) for vx, vy in room.vertices
        ]

        # calculate_polygon_area now accepts Sequence, so it won't complain
        new_area = calculate_polygon_area(snapped_vertices)

        snapped_room = replace(room, vertices=snapped_vertices, area=new_area)
        snapped_plan.append(snapped_room)

    plot_post_process(processed_floor_plan, snapped_plan)

    return snapped_plan
