from __future__ import annotations

from app.algorithms.floor_plan_post_processing import (
    INITIAL_GENERATION_PROFILE,
    PipelineStatus,
    PostProcessingProfile,
    PostProcessingRequest,
    ProcessorStatus,
    ProcessorUse,
    create_default_registry,
    post_process_floor_plan,
)
from app.algorithms.floor_plan_post_processing.config import (
    GridSnapConfig,
    HallwayMergeConfig,
    PlaceholderRemovalConfig,
    RectilinearSimplificationConfig,
    VerandaAdjustmentConfig,
    WallExtensionConfig,
)
from app.algorithms.floor_plan_post_processing.geometry import to_shapely
from app.algorithms.types_new import FloorPlan, RoomId, RoomRole, RoomType

from .conftest import polygon, rectangle, room


def run_one(plan, processor_id, config, *, required=False):
    profile = PostProcessingProfile(
        "one",
        (ProcessorUse(processor_id, config, required=required),),
        reject_existing_openings=False,
    )
    return post_process_floor_plan(
        PostProcessingRequest(plan, profile), registry=create_default_registry()
    )


def test_placeholder_removal_clears_rooms_and_references():
    plan = FloorPlan(
        rectangle(0, 0, 20, 20),
        [
            room("real", RoomType.VERANDA, rectangle(0, 0, 5, 5)),
            room(
                "placeholder",
                RoomType.OPEN_AREA,
                rectangle(5, 0, 10, 5),
                role=RoomRole.SOLVER_PLACEHOLDER,
                parent_room_id="real",
            ),
        ],
    )
    result = run_one(
        plan, "remove_placeholder_rooms", PlaceholderRemovalConfig(), required=True
    )
    assert result.status is PipelineStatus.SUCCESS
    assert [str(item.id) for item in plan.rooms] == ["real"]


def test_veranda_expands_into_associated_placeholder():
    plan = FloorPlan(
        rectangle(0, 0, 20, 20),
        [
            room("veranda", RoomType.VERANDA, rectangle(5, 0, 10, 5)),
            room(
                "reserved",
                RoomType.OPEN_AREA,
                rectangle(0, 0, 5, 5),
                role=RoomRole.SOLVER_PLACEHOLDER,
                parent_room_id="veranda",
            ),
        ],
    )
    profile = PostProcessingProfile(
        "veranda",
        (
            ProcessorUse("veranda_adjustment", VerandaAdjustmentConfig()),
            ProcessorUse(
                "remove_placeholder_rooms",
                PlaceholderRemovalConfig(),
                required=True,
            ),
        ),
        reject_existing_openings=False,
    )
    result = post_process_floor_plan(
        PostProcessingRequest(plan, profile), registry=create_default_registry()
    )
    assert result.status is PipelineStatus.SUCCESS
    assert result.executions[0].status is ProcessorStatus.CHANGED
    assert to_shapely(plan.rooms[0].boundary).bounds == (0.0, 0.0, 10.0, 5.0)


def test_wall_extension_fills_a_deterministic_recess_once():
    plan = FloorPlan(
        rectangle(0, 0, 30, 30),
        [
            room("living", RoomType.LIVING_ROOM, rectangle(0, 0, 20, 10)),
            room("kitchen", RoomType.KITCHEN, rectangle(0, 10, 10, 20)),
        ],
    )
    before = to_shapely(plan.rooms[0].boundary).area
    first = run_one(plan, "wall_extension", WallExtensionConfig())
    after = to_shapely(plan.rooms[0].boundary).area
    second = run_one(plan, "wall_extension", WallExtensionConfig())
    assert first.status is PipelineStatus.SUCCESS
    assert first.executions[0].status is ProcessorStatus.CHANGED
    assert after > before
    assert second.executions[0].status is ProcessorStatus.NOT_APPLICABLE


def test_hallway_merge_uses_stable_survivor_and_redirect():
    plan = FloorPlan(
        rectangle(0, 0, 30, 20),
        [
            room("hall-b", RoomType.HALLWAY, rectangle(10, 0, 20, 10)),
            room("hall-a", RoomType.HALLWAY, rectangle(0, 0, 10, 10)),
        ],
    )
    result = run_one(plan, "hallway_merge", HallwayMergeConfig(10))
    assert result.status is PipelineStatus.SUCCESS
    assert [str(item.id) for item in plan.rooms] == ["hall-a"]
    assert plan.identity_redirects == {RoomId("hall-b"): RoomId("hall-a")}
    assert tuple(map(str, plan.rooms[0].metadata.source_room_ids)) == (
        "hall-a",
        "hall-b",
    )


def test_grid_snap_is_idempotent():
    plan = FloorPlan(
        rectangle(0, 0, 20, 20),
        [room("bed", RoomType.BEDROOM, rectangle(0.1, 0.1, 9.7, 10.2))],
    )
    first = run_one(plan, "grid_snap", GridSnapConfig())
    boundary = plan.rooms[0].boundary
    second = run_one(plan, "grid_snap", GridSnapConfig())
    assert first.executions[0].status is ProcessorStatus.CHANGED
    assert second.executions[0].status is ProcessorStatus.NO_CHANGE
    assert plan.rooms[0].boundary == boundary


def test_simplifier_removes_redundant_rectilinear_vertices():
    plan = FloorPlan(
        rectangle(0, 0, 20, 20),
        [
            room(
                "bed",
                RoomType.BEDROOM,
                polygon((0, 0), (5, 0), (10, 0), (10, 10), (0, 10)),
            )
        ],
    )
    profile = PostProcessingProfile(
        "simplify",
        (
            ProcessorUse("grid_snap", GridSnapConfig()),
            ProcessorUse(
                "rectilinear_simplification", RectilinearSimplificationConfig()
            ),
        ),
        reject_existing_openings=False,
    )
    result = post_process_floor_plan(
        PostProcessingRequest(plan, profile), registry=create_default_registry()
    )
    assert result.status is PipelineStatus.SUCCESS
    assert len(plan.rooms[0].boundary.points) == 4


def test_complete_profile_removes_placeholder_and_is_repeatable():
    plan = FloorPlan(
        rectangle(0, 0, 30, 20),
        [
            room("veranda", RoomType.VERANDA, rectangle(5, 0, 10, 5)),
            room(
                "reserved",
                RoomType.OPEN_AREA,
                rectangle(0, 0, 5, 5),
                role=RoomRole.SOLVER_PLACEHOLDER,
                parent_room_id="veranda",
            ),
            room("bed", RoomType.BEDROOM, rectangle(10, 0, 20, 10)),
        ],
    )
    first = post_process_floor_plan(
        PostProcessingRequest(plan, INITIAL_GENERATION_PROFILE)
    )
    first_geometry = tuple(item.boundary for item in plan.rooms)
    second = post_process_floor_plan(
        PostProcessingRequest(plan, INITIAL_GENERATION_PROFILE)
    )
    assert first.status is PipelineStatus.SUCCESS
    assert second.status is PipelineStatus.SUCCESS
    assert all(item.role is RoomRole.STANDARD for item in plan.rooms)
    assert tuple(item.boundary for item in plan.rooms) == first_geometry
