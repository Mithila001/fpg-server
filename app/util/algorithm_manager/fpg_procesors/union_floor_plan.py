from dataclasses import dataclass
import os
import math
from datetime import datetime
from typing import TypedDict, Tuple

from app.core.fpg_rooms.config_fpg import ENABLE_PLOT_SAVING

import matplotlib

from app.algorithms.types.base import WallSegmentPayload
from app.algorithms.types.openings import FloorPlanWithOpenings

# Crucial: Forces headless rendering so Matplotlib doesn't attempt to open a GUI window
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import shapely
from shapely.geometry import Polygon, LineString, MultiLineString
from shapely.ops import unary_union


# --- Type Definitions ---
# class WallSegmentPayload(TypedDict):
#     x1: float
#     y1: float
#     x2: float
#     y2: float


@dataclass
class UnifiedFloorPlanPayload(TypedDict):
    walls: list[WallSegmentPayload]
    total_wall_length: float


# class ProcessedRoomData:
#     type: str
#     name: str
#     original_index: int
#     vertices: list[Tuple[float, float]]
#     area: float


# class OpeningData:
#     room_name: str
#     room_type: str
#     opening_type: str
#     side: str
#     x1: float
#     y1: float
#     x2: float
#     y2: float
#     connected_room_name: str
#     connected_room_type: str


# class FloorPlanWithOpenings:
#     floor_plan: list[ProcessedRoomData]
#     openings: list[OpeningData]


@dataclass
class UnionFloorPlanResult(TypedDict):
    floor_plan_with_openings: FloorPlanWithOpenings
    unified_floor_plan: UnifiedFloorPlanPayload


# --- Private Plotter Function ---
def _plot_union_floor_plan(walls: list[WallSegmentPayload]) -> None:
    """Generates and saves a visual representation of the merged wall network."""
    output_dir = os.path.join("test", "outputs", "union")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"union_floor_plan_{timestamp}.png")

    fig, ax = plt.subplots(figsize=(10, 10))

    for wall in walls:
        # Plot each unique segment
        ax.plot(
            [wall["x1"], wall["x2"]],
            [wall["y1"], wall["y2"]],
            color="black",
            linewidth=2.5,
            solid_capstyle="round",
        )

    ax.set_aspect("equal")
    ax.set_title("Unified Floor Plan - Shared Wall Network")
    plt.grid(True, linestyle=":", alpha=0.6)

    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close(fig)  # Free memory


# --- Main Processor ---
def union_floor_plan(
    floor_plan_with_openings: FloorPlanWithOpenings,
    tolerance: float = 1e-6,
) -> UnionFloorPlanResult:

    boundaries = []

    for room in floor_plan_with_openings.floor_plan:
        # Prevent errors from invalid data (like your verandaOutdoorSpace which has vertices=[])
        if not room.vertices or len(room.vertices) < 3:
            continue

        # 1. Create polygon
        poly = Polygon(room.vertices)

        # 2. Snap to grid to eliminate floating-point drift (crucial for removing artifacts)
        poly = shapely.set_precision(poly, grid_size=tolerance)

        # 3. We ONLY care about the boundary lines, not the area, to preserve inner walls
        boundaries.append(poly.boundary)

    # Edge case: no valid rooms
    if not boundaries:
        return {
            "floor_plan_with_openings": floor_plan_with_openings,
            "unified_floor_plan": {"walls": [], "total_wall_length": 0.0},
        }

    # 4. Union the lines. This is the magic step: it finds all overlaps, merges them into
    # single shared lines, and splits crossing lines at intersections (noding).
    merged_network = unary_union(boundaries)

    # 5. Extract the resulting geometries
    lines = []
    if isinstance(merged_network, LineString):
        lines = [merged_network]
    elif isinstance(merged_network, MultiLineString):
        lines = list(merged_network.geoms)
    elif hasattr(merged_network, "geoms"):
        # Fallback just in case it returns a GeometryCollection
        lines = [geom for geom in merged_network.geoms if isinstance(geom, LineString)]  # type: ignore

    unique_segments: list[WallSegmentPayload] = []
    total_length = 0.0

    # 6. Break the continuous line strings down into distinct 2-point wall segments
    for line in lines:
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i + 1]

            segment_length = math.dist(p1, p2)

            # Filter out zero-length anomalies
            if segment_length > tolerance:
                unique_segments.append(
                    {
                        "x1": float(p1[0]),
                        "y1": float(p1[1]),
                        "x2": float(p2[0]),
                        "y2": float(p2[1]),
                    }
                )
                total_length += segment_length

    # Plot and save to the test output directory (disabled in cloud via ENABLE_PLOT_SAVING=false)
    if ENABLE_PLOT_SAVING:
        _plot_union_floor_plan(unique_segments)

    return {
        "floor_plan_with_openings": floor_plan_with_openings,
        "unified_floor_plan": {
            "walls": unique_segments,
            "total_wall_length": round(total_length, 4),
        },
    }
