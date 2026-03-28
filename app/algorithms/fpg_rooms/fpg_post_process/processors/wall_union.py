from __future__ import annotations

from shapely.geometry import box
from shapely.ops import unary_union

from ..types import RoomBoundaryPayload, RoomWallsPayload, WallSegmentPayload, WallUnionResultPayload
from ..utils import extract_unique_segments


def run_wall_union(
    rooms: list[RoomBoundaryPayload],
    tolerance: float = 1e-6,
) -> WallUnionResultPayload:
    """Union all room boundaries and return deduplicated continuous wall segments."""
    if not rooms:
        return {
            "walls": [],
            "room_walls": {},
        }

    room_polygons: dict[str, object] = {
        room["name"]: box(room["x"], room["y"], room["x_end"], room["y_end"])
        for room in rooms
    }

    merged_boundaries = unary_union([poly.boundary for poly in room_polygons.values()])
    global_walls = extract_unique_segments(merged_boundaries, tolerance=tolerance)

    room_walls: dict[str, RoomWallsPayload] = {}
    for room in rooms:
        room_name = room["name"]
        clipped = merged_boundaries.intersection(room_polygons[room_name].boundary)
        unique_room_walls: list[WallSegmentPayload] = extract_unique_segments(clipped, tolerance=tolerance)
        room_walls[room_name] = {
            "room_name": room_name,
            "room_type": room["type"],
            "walls": unique_room_walls,
        }

    return {
        "walls": global_walls,
        "room_walls": room_walls,
    }
