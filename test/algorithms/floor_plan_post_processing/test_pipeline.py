from __future__ import annotations

from dataclasses import dataclass

from app.algorithms.floor_plan_post_processing import (
    FloorPlanProcessor,
    NumericPolicy,
    PipelineStatus,
    PostProcessingProfile,
    PostProcessingRequest,
    ProcessorOutcome,
    ProcessorRegistry,
    ProcessorStatus,
    ProcessorUse,
    post_process_floor_plan,
)
from app.algorithms.floor_plan_post_processing.config import GridSnapConfig
from app.algorithms.floor_plan_post_processing.processors import GridSnapProcessor
from app.algorithms.types_new import RoomId, RoomType

from .conftest import rectangle, room


@dataclass(frozen=True)
class DummyConfig:
    fail: bool = False


class DummyProcessor(FloorPlanProcessor):
    processor_id = "dummy"
    description = "test processor"
    config_type = DummyConfig

    def process(self, floor_plan, context, config):
        floor_plan.rooms.append(
            room("added", RoomType.BEDROOM, rectangle(20, 20, 21, 21))
        )
        if config.fail:
            raise RuntimeError("boom")
        return ProcessorOutcome(ProcessorStatus.CHANGED, "added", (RoomId("added"),))


class DependentProcessor(DummyProcessor):
    processor_id = "dependent"
    prerequisites = ("dummy",)


def profile(*uses: ProcessorUse) -> PostProcessingProfile:
    return PostProcessingProfile(
        "test", uses, NumericPolicy(), reject_existing_openings=False
    )


def test_success_mutates_and_returns_same_floor_plan(empty_plan):
    result = post_process_floor_plan(
        PostProcessingRequest(
            empty_plan, profile(ProcessorUse("dummy", DummyConfig()))
        ),
        registry=ProcessorRegistry((DummyProcessor(),)),
    )
    assert result.status is PipelineStatus.SUCCESS
    assert result.floor_plan is empty_plan
    assert [str(item.id) for item in empty_plan.rooms] == ["added"]


def test_best_effort_failure_rolls_back_and_skips_dependent(empty_plan):
    result = post_process_floor_plan(
        PostProcessingRequest(
            empty_plan,
            profile(
                ProcessorUse("dummy", DummyConfig(fail=True)),
                ProcessorUse("dependent", DummyConfig()),
            ),
        ),
        registry=ProcessorRegistry((DummyProcessor(), DependentProcessor())),
    )
    assert result.status is PipelineStatus.SUCCESS
    assert empty_plan.rooms == []
    assert result.executions[0].status is ProcessorStatus.FAILED
    assert result.executions[0].rolled_back
    assert result.executions[1].status is ProcessorStatus.SKIPPED


def test_required_failure_returns_failed_stable_plan(empty_plan):
    result = post_process_floor_plan(
        PostProcessingRequest(
            empty_plan,
            profile(ProcessorUse("dummy", DummyConfig(fail=True), required=True)),
        ),
        registry=ProcessorRegistry((DummyProcessor(),)),
    )
    assert result.status is PipelineStatus.FAILED
    assert empty_plan.rooms == []


def test_preflight_rejects_missing_or_misordered_prerequisite(empty_plan):
    result = post_process_floor_plan(
        PostProcessingRequest(
            empty_plan,
            profile(ProcessorUse("dependent", DummyConfig())),
        ),
        registry=ProcessorRegistry((DependentProcessor(),)),
    )
    assert result.status is PipelineStatus.FAILED
    assert result.failure is not None
    assert result.failure.code == "invalid_configuration"


def test_preflight_rejects_unknown_processor_and_wrong_config(empty_plan):
    unknown = post_process_floor_plan(
        PostProcessingRequest(
            empty_plan, profile(ProcessorUse("missing", DummyConfig()))
        ),
        registry=ProcessorRegistry(),
    )
    wrong = post_process_floor_plan(
        PostProcessingRequest(
            empty_plan, profile(ProcessorUse("dummy", GridSnapConfig()))
        ),
        registry=ProcessorRegistry((DummyProcessor(),)),
    )
    assert unknown.status is PipelineStatus.FAILED
    assert wrong.status is PipelineStatus.FAILED


def test_registry_rejects_duplicate_ids():
    try:
        ProcessorRegistry((DummyProcessor(), DummyProcessor()))
    except Exception as exc:
        assert getattr(exc, "code", None) == "invalid_configuration"
    else:
        raise AssertionError("duplicate registration should fail")


def test_required_grid_snap_rolls_back_collapsed_room(empty_plan):
    empty_plan.rooms.append(
        room("tiny", RoomType.BEDROOM, rectangle(0.1, 0.1, 0.4, 0.4))
    )
    original = empty_plan.rooms[0].boundary
    result = post_process_floor_plan(
        PostProcessingRequest(
            empty_plan,
            profile(ProcessorUse("grid_snap", GridSnapConfig(), required=True)),
        ),
        registry=ProcessorRegistry((GridSnapProcessor(),)),
    )
    assert result.status is PipelineStatus.FAILED
    assert empty_plan.rooms[0].boundary == original
