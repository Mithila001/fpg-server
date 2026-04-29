from datetime import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from dataclasses import dataclass
from typing import Tuple, Any

from shapely.geometry import Polygon, MultiLineString, LineString
from shapely.ops import unary_union

from app.algorithms.fpg_post_processor.snap_floor_plan_to_grid import ProcessedRoomData
from app.algorithms.types.domain import UnifiedFloorPlan, WallSegment




def floor_plan_wall_union(
    processed_floor_plan: list[ProcessedRoomData], 
    tolerance: float = 1e-6
) -> UnifiedFloorPlan:
    """
    Unions room boundaries to extract unique, non-overlapping wall segments
    from a processed floor plan.
    """
    if not processed_floor_plan:
        return UnifiedFloorPlan(segments=[], total_wall_length=0.0)

    # 1. Convert vertices to Polygons and get their boundaries (LinearRings)
    boundaries = []
    for room in processed_floor_plan:
        if len(room.vertices) < 3:
            continue
        poly = Polygon(room.vertices)
        boundaries.append(poly.boundary)

    # 2. Perform the Union
    # This merges overlapping lines into a single geometric structure
    unified_geometry = unary_union(boundaries)

    # 3. Extract segments and clean up geometry
    # We ensure we are working with a list of LineStrings
    if isinstance(unified_geometry, LineString):
        raw_lines = [unified_geometry]
    elif isinstance(unified_geometry, MultiLineString):
        raw_lines = list(unified_geometry.geoms)
    else:
        raw_lines = []

    wall_segments = []
    total_length = 0.0

    for line in raw_lines:
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            x1, y1 = coords[i][:2]
            x2, y2 = coords[i+1][:2]
            
            dist = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
            
            if dist > tolerance:
                wall_segments.append(WallSegment(
                    start=(x1, y1), 
                    end=(x2, y2), 
                    length=round(dist, 4)
                ))
                total_length += dist
    # _plot_wall_union_result(result=UnifiedFloorPlan(segments=wall_segments, total_wall_length=total_length), filename_prefix="wall_union_")
    return UnifiedFloorPlan(
        segments=wall_segments,
        total_wall_length=round(total_length, 4)
    )


def _plot_wall_union_result(
    result: UnifiedFloorPlan, 
    filename_prefix: str = "wall_union"
) -> None:
    """
    Visualizes unified wall segments and saves with a timestamp.
    """
    # 1. Create timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.png"

    # 2. Setup absolute pathing
    # This ensures it saves relative to your project root regardless of where you run the script
    base_dir = os.path.abspath(os.getcwd())
    output_dir = os.path.join(base_dir, "test/outputs/post_process/wall_union")
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, filename)

    # 3. Plotting logic
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(12, 12))

    if result.segments:
        # Convert segments to the format LineCollection expects
        lines = [[seg.start, seg.end] for seg in result.segments]
        lc = LineCollection(lines, colors='royalblue', linewidths=2, label="Unified Walls")
        ax.add_collection(lc)
        ax.autoscale()
    
    ax.set_aspect('equal')
    ax.set_title(f"Wall Union Result\n{timestamp} | {len(result.segments)} segments", fontsize=14)
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.xlabel("X (units)")
    plt.ylabel("Y (units)")

    # 4. Save and cleanup
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    print(f"✅ Plot successfully saved to: {save_path}")
    plt.close(fig)