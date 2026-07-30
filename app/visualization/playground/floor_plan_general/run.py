from __future__ import annotations

from copy import deepcopy

from fpg_core.types import (
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

from app.visualization.api import (
    FloorPlanFlowVisualization,
    FloorPlanVisualizationStage,
    render_floor_plan_general,
)


def rectangle(x1: int, y1: int, x2: int, y2: int) -> Polygon:
    return Polygon(
        points=(
            Point(x1, y1),
            Point(x2, y1),
            Point(x2, y2),
            Point(x1, y2),
        )
    )


def build_initial_floor_plan() -> FloorPlan:
    return FloorPlan(
        boundary=rectangle(0, 0, 120, 80),
        rooms=[
            FloorPlanRoom(
                id=RoomId("living"),
                room_type=RoomType.LIVING_ROOM,
                name="Living Room",
                boundary=rectangle(0, 0, 60, 40),
            ),
            FloorPlanRoom(
                id=RoomId("kitchen"),
                room_type=RoomType.KITCHEN,
                name="Kitchen",
                boundary=rectangle(60, 0, 120, 40),
            ),
            FloorPlanRoom(
                id=RoomId("bedroom_1"),
                room_type=RoomType.BEDROOM,
                name="Bedroom 1",
                boundary=rectangle(0, 40, 60, 80),
            ),
            FloorPlanRoom(
                id=RoomId("bedroom_2"),
                room_type=RoomType.BEDROOM,
                name="Bedroom 2",
                boundary=rectangle(60, 40, 120, 80),
            ),
        ],
    )


def main() -> None:
    initial = build_initial_floor_plan()

    post_processed = deepcopy(initial)
    post_processed.applied_transformations.add("grid_snap")

    with_openings = deepcopy(post_processed)
    with_openings.openings.extend(
        [
            FloorPlanOpening(
                id=OpeningId("main_door"),
                opening_type=OpeningType.DOOR,
                purpose=OpeningPurpose.MAIN_ENTRANCE,
                start=Point(20, 0),
                end=Point(30, 0),
                connected_room_ids=(RoomId("living"),),
            ),
            FloorPlanOpening(
                id=OpeningId("living_window"),
                opening_type=OpeningType.WINDOW,
                purpose=OpeningPurpose.DAYLIGHT,
                start=Point(0, 15),
                end=Point(0, 30),
                connected_room_ids=(RoomId("living"),),
            ),
        ]
    )

    payload = FloorPlanFlowVisualization(
        stages=(
            FloorPlanVisualizationStage(
                stage_id="solver_initial",
                stage_name="Initial Generation",
                category="solver",
                profile_name="initial_generation",
                floor_plan=initial,
            ),
            FloorPlanVisualizationStage(
                stage_id="post_grid_snap",
                stage_name="Grid Snap",
                category="post_processing",
                profile_name="grid_snap",
                floor_plan=post_processed,
            ),
            FloorPlanVisualizationStage(
                stage_id="opening_generation",
                stage_name="Doors and Windows",
                category="openings",
                profile_name=None,
                floor_plan=with_openings,
            ),
        )
    )

    output_path = render_floor_plan_general(
        payload,
        run_id="playground",
        output_prefix="generation_flow",
    )
    print(f"Floor-plan flow PNG: {output_path}")


if __name__ == "__main__":
    main()
