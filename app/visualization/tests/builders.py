from __future__ import annotations

from app.algorithms.types_new import (
    FloorPlan,
    FloorPlanOpening,
    FloorPlanRoom,
    OpeningId,
    OpeningPurpose,
    OpeningType,
    Point,
    Polygon,
    RoomId,
    RoomType,
)

from ..models import GraphEdge, GraphNode, PathOverlay, PointMarker, ZoneOverlay


def rectangle(left: float, bottom: float, right: float, top: float) -> Polygon:
    return Polygon(
        points=(
            Point(left, bottom),
            Point(right, bottom),
            Point(right, top),
            Point(left, top),
        )
    )


def build_floor_plan() -> FloorPlan:
    return FloorPlan(
        boundary=rectangle(0, 0, 100, 80),
        rooms=[
            FloorPlanRoom(
                id=RoomId("living"),
                room_type=RoomType.LIVING_ROOM,
                name="Living Room",
                boundary=rectangle(0, 0, 55, 45),
            ),
            FloorPlanRoom(
                id=RoomId("kitchen"),
                room_type=RoomType.KITCHEN,
                name="Kitchen",
                boundary=rectangle(55, 0, 100, 45),
            ),
            FloorPlanRoom(
                id=RoomId("bedroom"),
                room_type=RoomType.BEDROOM,
                name="Bedroom",
                boundary=rectangle(0, 45, 60, 80),
            ),
            FloorPlanRoom(
                id=RoomId("bathroom"),
                room_type=RoomType.BATHROOM,
                name="Bathroom",
                boundary=rectangle(60, 45, 100, 80),
            ),
        ],
        openings=[
            FloorPlanOpening(
                id=OpeningId("door-1"),
                opening_type=OpeningType.DOOR,
                purpose=OpeningPurpose.ROOM_CONNECTION,
                start=Point(52, 45),
                end=Point(60, 45),
                connected_room_ids=(RoomId("living"), RoomId("bedroom")),
            ),
            FloorPlanOpening(
                id=OpeningId("window-1"),
                opening_type=OpeningType.WINDOW,
                purpose=OpeningPurpose.DAYLIGHT,
                start=Point(20, 80),
                end=Point(40, 80),
                connected_room_ids=(RoomId("bedroom"),),
            ),
        ],
    )


def build_point_map_data() -> tuple[list[PointMarker], list[ZoneOverlay], list[PathOverlay]]:
    markers = [
        PointMarker(15, 20, label="Living", value=88.5, radius_units=3.0),
        PointMarker(70, 25, label="Kitchen", value=74.0),
        PointMarker(30, 65, label="Bedroom", value=91.0),
    ]
    zones = [
        ZoneOverlay(
            points=((0, 0), (50, 0), (50, 45), (0, 45)),
            label="Public zone",
        )
    ]
    paths = [
        PathOverlay(
            points=((15, 20), (40, 35), (70, 25)),
            label="Candidate path",
            arrow_at_end=True,
        )
    ]
    return markers, zones, paths


def build_graph_data() -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes = [
        GraphNode("living", 20, 25, label="Living", value=92),
        GraphNode("kitchen", 65, 20, label="Kitchen", value=80),
        GraphNode("bedroom", 35, 65, label="Bedroom", value=87),
    ]
    edges = [
        GraphEdge("living", "kitchen", label="adjacent", highlighted=True),
        GraphEdge("living", "bedroom", label="path", directed=True),
    ]
    return nodes, edges
