from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from Restructure_Data.floor_plan_spec import (
    ConstraintStrength,
    FloorPlanGenerationSpec,
    FloorSpec,
    MatchPolicy,
    RoomId,
    RoomRelationSpec,
    RoomSizeSpec,
    RoomSpec,
    RoomType,
)
from app.algorithms.floor_plan_scoring import (
    CRITICAL_GROUP,
    FUNCTIONAL_GROUP,
    DEFAULT_SCORING_PROFILE,
    EvaluationStatus,
    EvaluatorContractError,
    EvaluatorExecutionError,
    EvaluatorKey,
    EvaluatorRegistry,
    EvaluatorResult,
    EvaluatorRule,
    FloorPlanScoreManager,
    GroupKey,
    GroupStatus,
    ScoringConfigurationError,
    ScoringGroupRule,
    ScoringInputError,
    ScoringProfile,
    create_default_registry,
    score_floor_plan,
)
from app.algorithms.floor_plan_scoring.context import ScoringContext
from app.algorithms.floor_plan_scoring.evaluators.base import FloorPlanEvaluator


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Polygon:
    points: tuple[Point, ...]


@dataclass(frozen=True)
class Room:
    id: RoomId
    room_type: RoomType
    name: str
    boundary: Polygon


@dataclass(frozen=True)
class Plan:
    boundary: Polygon
    rooms: tuple[Room, ...]
    openings: tuple[object, ...] = ()


@dataclass(frozen=True)
class NoSettings:
    pass


class FixedEvaluator(FloorPlanEvaluator):
    def __init__(self, key: str, score: float | None, *, raises: bool = False) -> None:
        self._key = EvaluatorKey(key)
        self._score = score
        self._raises = raises

    @property
    def key(self) -> EvaluatorKey:
        return self._key

    @property
    def settings_type(self) -> type[object]:
        return NoSettings

    def evaluate(self, context: ScoringContext, settings: object) -> EvaluatorResult:
        if self._raises:
            raise RuntimeError("boom")
        if self._score is None:
            return EvaluatorResult(self.key, EvaluationStatus.NOT_APPLICABLE, None)
        return EvaluatorResult(self.key, EvaluationStatus.COMPLETED, self._score)


def rectangle(x1: float, y1: float, x2: float, y2: float) -> Polygon:
    return Polygon((Point(x1, y1), Point(x2, y1), Point(x2, y2), Point(x1, y2)))


def room_spec(
    room_id: str,
    room_type: RoomType,
    *,
    required: bool = True,
    min_area: float = 1.0,
    max_area: float = 1000.0,
) -> RoomSpec:
    return RoomSpec(
        id=RoomId(room_id),
        room_type=room_type,
        name=room_id.replace("_", " ").title(),
        size=RoomSizeSpec(1.0, 100.0, 1.0, 100.0, min_area, max_area),
        required=required,
    )


def specification(
    specs: tuple[RoomSpec, ...],
    relations: tuple[RoomRelationSpec, ...] = (),
    *,
    width: float = 20.0,
    height: float = 10.0,
) -> FloorPlanGenerationSpec:
    return FloorPlanGenerationSpec(FloorSpec(width, height), specs, relations)


def valid_pair() -> tuple[Plan, FloorPlanGenerationSpec]:
    specs = (
        room_spec("living", RoomType.LIVING_ROOM),
        room_spec("kitchen", RoomType.KITCHEN),
    )
    plan = Plan(
        boundary=rectangle(0, 0, 20, 10),
        rooms=(
            Room(
                RoomId("living"),
                RoomType.LIVING_ROOM,
                "Living",
                rectangle(0, 0, 10, 10),
            ),
            Room(
                RoomId("kitchen"), RoomType.KITCHEN, "Kitchen", rectangle(10, 0, 20, 10)
            ),
        ),
    )
    return plan, specification(specs)


def test_default_profile_normalizes_two_groups_to_fifty_each() -> None:
    plan, spec = valid_pair()
    result = score_floor_plan(plan, spec)

    assert result.total_score == pytest.approx(100.0)
    assert result.passed_critical is True
    assert [group.normalized_maximum for group in result.group_results] == [50.0, 50.0]


def test_critical_failure_returns_partial_critical_score_and_skips_functional() -> None:
    plan, spec = valid_pair()
    diagonal = Room(
        RoomId("living"),
        RoomType.LIVING_ROOM,
        "Living",
        Polygon((Point(0, 0), Point(10, 0), Point(8, 10), Point(0, 10))),
    )
    broken = replace(plan, rooms=(diagonal, plan.rooms[1]))

    result = score_floor_plan(broken, spec)

    assert result.passed_critical is False
    assert result.critical_failure is not None
    assert result.total_score < 50.0
    functional = [
        item for item in result.evaluator_results if item.group_key == FUNCTIONAL_GROUP
    ]
    assert functional
    assert all(item.status is EvaluationStatus.SKIPPED for item in functional)


def test_all_critical_evaluators_execute_before_gate_stops_later_groups() -> None:
    plan, spec = valid_pair()
    diagonal = replace(
        plan.rooms[0],
        boundary=Polygon((Point(0, 0), Point(10, 0), Point(8, 10), Point(0, 10))),
    )
    result = score_floor_plan(replace(plan, rooms=(diagonal, plan.rooms[1])), spec)
    critical = [
        item for item in result.evaluator_results if item.group_key == CRITICAL_GROUP
    ]

    assert len(critical) == 4
    assert all(item.status is not EvaluationStatus.SKIPPED for item in critical)


def test_missing_required_room_raises_typed_input_error() -> None:
    plan, spec = valid_pair()
    with pytest.raises(ScoringInputError, match="Required rooms are missing"):
        score_floor_plan(replace(plan, rooms=(plan.rooms[0],)), spec)


def test_missing_optional_room_is_allowed() -> None:
    plan, spec = valid_pair()
    optional_kitchen = replace(spec.rooms[1], required=False)
    optional_spec = replace(spec, rooms=(spec.rooms[0], optional_kitchen))

    result = score_floor_plan(replace(plan, rooms=(plan.rooms[0],)), optional_spec)

    assert result.passed_critical is True


def test_unknown_room_and_room_type_mismatch_raise_input_error() -> None:
    plan, spec = valid_pair()
    unknown = replace(plan.rooms[0], id=RoomId("unknown"))
    with pytest.raises(ScoringInputError, match="unknown room ID"):
        score_floor_plan(replace(plan, rooms=(unknown, plan.rooms[1])), spec)

    wrong_type = replace(plan.rooms[0], room_type=RoomType.BEDROOM)
    with pytest.raises(ScoringInputError, match="does not match specification"):
        score_floor_plan(replace(plan, rooms=(wrong_type, plan.rooms[1])), spec)


def test_hard_adjacency_relation_passes_with_required_shared_boundary() -> None:
    plan, spec = valid_pair()
    relation = RoomRelationSpec(
        source_room_id=RoomId("living"),
        target_room_ids=(RoomId("kitchen"),),
        match_policy=MatchPolicy.AND,
        strength=ConstraintStrength.HARD,
    )
    result = score_floor_plan(plan, replace(spec, room_relations=(relation,)))
    adjacency = next(
        item
        for item in result.evaluator_results
        if str(item.evaluator_key) == "required_adjacency"
    )
    assert adjacency.raw_score == 100.0


def test_enclosed_void_is_reported_as_a_critical_failure() -> None:
    specs = tuple(
        room_spec(room_id, RoomType.BEDROOM)
        for room_id in ("bottom", "top", "left", "right")
    )
    plan = Plan(
        rectangle(0, 0, 3, 3),
        (
            Room(RoomId("bottom"), RoomType.BEDROOM, "Bottom", rectangle(0, 0, 3, 1)),
            Room(RoomId("top"), RoomType.BEDROOM, "Top", rectangle(0, 2, 3, 3)),
            Room(RoomId("left"), RoomType.BEDROOM, "Left", rectangle(0, 1, 1, 2)),
            Room(RoomId("right"), RoomType.BEDROOM, "Right", rectangle(2, 1, 3, 2)),
        ),
    )

    result = score_floor_plan(plan, specification(specs, width=3, height=3))
    void_result = next(
        item
        for item in result.evaluator_results
        if str(item.evaluator_key) == "enclosed_voids"
    )

    assert void_result.raw_score == 0.0
    assert result.passed_critical is False


def test_long_open_recess_is_reported_without_being_an_enclosed_void() -> None:
    specs = tuple(
        room_spec(room_id, RoomType.BEDROOM) for room_id in ("bottom", "left", "right")
    )
    plan = Plan(
        rectangle(0, 0, 10, 30),
        (
            Room(RoomId("bottom"), RoomType.BEDROOM, "Bottom", rectangle(0, 0, 10, 2)),
            Room(RoomId("left"), RoomType.BEDROOM, "Left", rectangle(0, 2, 2, 30)),
            Room(RoomId("right"), RoomType.BEDROOM, "Right", rectangle(8, 2, 10, 30)),
        ),
    )

    result = score_floor_plan(plan, specification(specs, width=10, height=30))
    recess = next(
        item
        for item in result.evaluator_results
        if str(item.evaluator_key) == "inward_recess"
    )
    voids = next(
        item
        for item in result.evaluator_results
        if str(item.evaluator_key) == "enclosed_voids"
    )

    assert recess.raw_score == 0.0
    assert voids.raw_score == 100.0


def test_bedroom_quality_uses_room_size_specification() -> None:
    spec = specification(
        (room_spec("bed", RoomType.BEDROOM, min_area=100.0, max_area=200.0),),
        width=10,
        height=10,
    )
    plan = Plan(
        rectangle(0, 0, 10, 10),
        (Room(RoomId("bed"), RoomType.BEDROOM, "Bed", rectangle(0, 0, 10, 5)),),
    )

    result = score_floor_plan(plan, spec)
    bedroom = next(
        item
        for item in result.evaluator_results
        if str(item.evaluator_key) == "bedroom_quality"
    )

    assert bedroom.raw_score is not None
    assert bedroom.raw_score < 100.0
    assert any(
        finding.code == "BEDROOM_BELOW_MINIMUM_AREA" for finding in bedroom.findings
    )


def test_not_applicable_evaluators_redistribute_within_and_across_groups() -> None:
    spec = specification((room_spec("garage", RoomType.GARAGE),))
    plan = Plan(
        rectangle(0, 0, 20, 10),
        (Room(RoomId("garage"), RoomType.GARAGE, "Garage", rectangle(0, 0, 20, 10)),),
    )
    result = score_floor_plan(plan, spec)

    critical = next(
        group for group in result.group_results if group.group_key == CRITICAL_GROUP
    )
    functional = next(
        group for group in result.group_results if group.group_key == FUNCTIONAL_GROUP
    )
    assert critical.normalized_maximum == 100.0
    assert functional.status is GroupStatus.NOT_APPLICABLE
    assert result.total_score == 100.0


def test_disabling_a_group_does_not_require_disabling_each_of_its_evaluators() -> None:
    plan, spec = valid_pair()
    profile = replace(
        DEFAULT_SCORING_PROFILE,
        groups=tuple(
            replace(group, enabled=False) if group.key == FUNCTIONAL_GROUP else group
            for group in DEFAULT_SCORING_PROFILE.groups
        ),
    )

    result = FloorPlanScoreManager(create_default_registry(), profile).score(plan, spec)

    assert len(result.group_results) == 1
    assert result.group_results[0].normalized_maximum == 100.0
    assert result.total_score == 100.0


def test_custom_evaluator_weights_are_normalized_within_group() -> None:
    plan, spec = valid_pair()
    registry = EvaluatorRegistry(
        (
            FixedEvaluator("gate", 100.0),
            FixedEvaluator("low", 0.0),
            FixedEvaluator("high", 100.0),
        )
    )
    profile = ScoringProfile(
        groups=(
            ScoringGroupRule(CRITICAL_GROUP, order=10),
            ScoringGroupRule(FUNCTIONAL_GROUP, order=20),
        ),
        evaluators=(
            EvaluatorRule(
                EvaluatorKey("gate"), CRITICAL_GROUP, NoSettings(), minimum_score=100.0
            ),
            EvaluatorRule(
                EvaluatorKey("low"), FUNCTIONAL_GROUP, NoSettings(), weight=1.0
            ),
            EvaluatorRule(
                EvaluatorKey("high"), FUNCTIONAL_GROUP, NoSettings(), weight=3.0
            ),
        ),
    )

    result = FloorPlanScoreManager(registry, profile).score(plan, spec)

    assert result.total_score == pytest.approx(87.5)


def test_four_equal_groups_receive_twenty_five_points_each() -> None:
    plan, spec = valid_pair()
    group_keys = (
        CRITICAL_GROUP,
        FUNCTIONAL_GROUP,
        GroupKey("aesthetic"),
        GroupKey("extra"),
    )
    evaluators = tuple(FixedEvaluator(f"score_{index}", 100.0) for index in range(4))
    profile = ScoringProfile(
        groups=tuple(
            ScoringGroupRule(key, order=(index + 1) * 10)
            for index, key in enumerate(group_keys)
        ),
        evaluators=tuple(
            EvaluatorRule(
                evaluator.key,
                group_keys[index],
                NoSettings(),
                minimum_score=100.0 if index == 0 else None,
            )
            for index, evaluator in enumerate(evaluators)
        ),
    )
    result = FloorPlanScoreManager(EvaluatorRegistry(evaluators), profile).score(
        plan, spec
    )

    assert [group.normalized_maximum for group in result.group_results] == [25.0] * 4
    assert result.total_score == 100.0


def test_invalid_profile_and_unexpected_execution_failure_raise_typed_errors() -> None:
    plan, spec = valid_pair()
    bad_profile = replace(
        DEFAULT_SCORING_PROFILE,
        groups=(
            ScoringGroupRule(CRITICAL_GROUP, order=10),
            ScoringGroupRule(CRITICAL_GROUP, order=20),
        ),
    )
    with pytest.raises(ScoringConfigurationError, match="configured more than once"):
        FloorPlanScoreManager(create_default_registry(), bad_profile)

    evaluator = FixedEvaluator("explode", 100.0, raises=True)
    profile = ScoringProfile(
        groups=(ScoringGroupRule(CRITICAL_GROUP),),
        evaluators=(
            EvaluatorRule(
                evaluator.key,
                CRITICAL_GROUP,
                NoSettings(),
                minimum_score=100.0,
            ),
        ),
    )
    with pytest.raises(EvaluatorExecutionError, match="failed unexpectedly"):
        FloorPlanScoreManager(EvaluatorRegistry((evaluator,)), profile).score(
            plan, spec
        )


def test_invalid_evaluator_score_and_empty_critical_gate_raise_typed_errors() -> None:
    plan, spec = valid_pair()
    invalid = FixedEvaluator("invalid", 101.0)
    invalid_profile = ScoringProfile(
        groups=(ScoringGroupRule(CRITICAL_GROUP),),
        evaluators=(
            EvaluatorRule(
                invalid.key,
                CRITICAL_GROUP,
                NoSettings(),
                minimum_score=100.0,
            ),
        ),
    )
    with pytest.raises(EvaluatorContractError, match="between 0 and 100"):
        FloorPlanScoreManager(EvaluatorRegistry((invalid,)), invalid_profile).score(
            plan, spec
        )

    not_applicable = FixedEvaluator("not_applicable", None)
    empty_gate_profile = replace(
        invalid_profile,
        evaluators=(
            EvaluatorRule(
                not_applicable.key,
                CRITICAL_GROUP,
                NoSettings(),
                minimum_score=100.0,
            ),
        ),
    )
    with pytest.raises(EvaluatorExecutionError, match="no applicable"):
        FloorPlanScoreManager(
            EvaluatorRegistry((not_applicable,)), empty_gate_profile
        ).score(plan, spec)


def test_floor_plan_module_is_not_imported_by_package_import() -> None:
    import sys
    import app.algorithms.floor_plan_scoring  # noqa: F401

    assert "Restructure_Data.floor_plan" not in sys.modules


def test_non_finite_coordinate_raises_input_error() -> None:
    plan, spec = valid_pair()
    invalid_boundary = Polygon(
        (Point(0, 0), Point(float("nan"), 0), Point(10, 10), Point(0, 10))
    )
    with pytest.raises(ScoringInputError, match="must be finite"):
        score_floor_plan(
            replace(
                plan,
                rooms=(
                    replace(plan.rooms[0], boundary=invalid_boundary),
                    plan.rooms[1],
                ),
            ),
            spec,
        )
