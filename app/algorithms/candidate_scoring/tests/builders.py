from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    EvaluatorCategory,
    EvaluatorKey,
    EvaluatorRule,
    ScoringConfig,
)
from app.algorithms.types_new import (
    FloorPlanGenerationSpec,
    FloorSpec,
    RoomId,
    RoomSizeSpec,
    RoomSpec,
    RoomType,
)

DEFAULT_FLOOR_WIDTH = 120.0
DEFAULT_FLOOR_HEIGHT = 100.0
DEFAULT_ROOM_SIZE = RoomSizeSpec(
    min_width=20.0,
    max_width=50.0,
    min_height=20.0,
    max_height=50.0,
    min_area=400.0,
    max_area=2500.0,
)

# id, type, display name, candidate x, candidate y
DEFAULT_ROOM_LAYOUT: tuple[tuple[str, RoomType, str, float, float], ...] = (
    ("veranda_1", RoomType.VERANDA, "Veranda", 60.0, 10.0),
    ("garage_1", RoomType.GARAGE, "Garage", 15.0, 15.0),
    ("living_1", RoomType.LIVING_ROOM, "Living Room", 60.0, 30.0),
    ("kitchen_1", RoomType.KITCHEN, "Kitchen", 95.0, 55.0),
    ("dining_1", RoomType.DINING_ROOM, "Dining Room", 75.0, 55.0),
    ("hallway_1", RoomType.HALLWAY, "Hallway", 60.0, 60.0),
    ("bedroom_1", RoomType.BEDROOM, "Bedroom 1", 25.0, 75.0),
    ("bedroom_2", RoomType.BEDROOM, "Bedroom 2", 55.0, 75.0),
    ("bathroom_1", RoomType.BATHROOM, "Bathroom", 90.0, 80.0),
    (
        "attached_bathroom_1",
        RoomType.ATTACHED_BATHROOM,
        "Attached Bathroom",
        25.0,
        90.0,
    ),
)


def build_generation_spec(
    *,
    width: float = DEFAULT_FLOOR_WIDTH,
    height: float = DEFAULT_FLOOR_HEIGHT,
    room_layout: Sequence[tuple[str, RoomType, str, float, float]] = DEFAULT_ROOM_LAYOUT,
) -> FloorPlanGenerationSpec:
    """Build a valid typed floor-plan specification."""

    rooms = tuple(
        RoomSpec(
            id=RoomId(room_id),
            room_type=room_type,
            name=name,
            size=DEFAULT_ROOM_SIZE,
        )
        for room_id, room_type, name, _, _ in room_layout
    )
    return FloorPlanGenerationSpec(
        floor=FloorSpec(width=width, height=height),
        rooms=rooms,
        room_relations=(),
    )


def build_candidate_points(
    *,
    room_layout: Sequence[tuple[str, RoomType, str, float, float]] = DEFAULT_ROOM_LAYOUT,
    include_room_ids: Iterable[str] | None = None,
    coordinate_overrides: Mapping[str, tuple[float, float]] | None = None,
    include_metadata: bool = False,
) -> dict[str, dict[str, Any]]:
    """Build valid room candidate points with optional focused overrides."""

    allowed_ids = set(include_room_ids) if include_room_ids is not None else None
    overrides = dict(coordinate_overrides or {})
    points: dict[str, dict[str, Any]] = {}

    for room_id, room_type, name, default_x, default_y in room_layout:
        if allowed_ids is not None and room_id not in allowed_ids:
            continue

        x, y = overrides.get(room_id, (default_x, default_y))
        point: dict[str, Any] = {"x": x, "y": y}
        if include_metadata:
            point.update(
                {
                    "room_id": room_id,
                    "room_type": room_type.value,
                    "name": name,
                }
            )
        points[room_id] = point

    return points


def build_scoring_input(
    *,
    specification: Any | None = None,
    candidate: Any | None = None,
    width: float = DEFAULT_FLOOR_WIDTH,
    height: float = DEFAULT_FLOOR_HEIGHT,
    room_layout: Sequence[tuple[str, RoomType, str, float, float]] = DEFAULT_ROOM_LAYOUT,
    include_room_ids: Iterable[str] | None = None,
    coordinate_overrides: Mapping[str, tuple[float, float]] | None = None,
) -> CandidateScoringInput:
    """Build a valid framework input using the project's typed specification."""

    resolved_specification = specification
    if resolved_specification is None:
        resolved_specification = build_generation_spec(
            width=width,
            height=height,
            room_layout=room_layout,
        )

    resolved_candidate = candidate
    if resolved_candidate is None:
        resolved_candidate = build_candidate_points(
            room_layout=room_layout,
            include_room_ids=include_room_ids,
            coordinate_overrides=coordinate_overrides,
        )

    return CandidateScoringInput(
        specification=resolved_specification,
        candidate=resolved_candidate,
    )


def build_rule(
    key: str,
    *,
    category: EvaluatorCategory = EvaluatorCategory.QUALITY,
    enabled: bool = True,
    order: int = 0,
    weight: float = 1.0,
    minimum_score: float | None = None,
    settings: Mapping[str, Any] | None = None,
) -> EvaluatorRule:
    """Build one valid evaluator rule by default."""

    if category is EvaluatorCategory.CRITICAL and minimum_score is None:
        minimum_score = 50.0

    return EvaluatorRule(
        key=EvaluatorKey(key),
        category=category,
        enabled=enabled,
        order=order,
        weight=weight,
        minimum_score=minimum_score,
        settings=settings or {},
    )


def build_scoring_config(
    *rules: EvaluatorRule,
    fail_fast_on_critical_failure: bool = True,
    not_applicable_quality_contributes: bool = False,
    raise_on_evaluator_error: bool = False,
) -> ScoringConfig:
    """Build a scoring configuration from explicit rules."""

    return ScoringConfig(
        evaluator_rules=tuple(rules),
        fail_fast_on_critical_failure=fail_fast_on_critical_failure,
        not_applicable_quality_contributes=not_applicable_quality_contributes,
        raise_on_evaluator_error=raise_on_evaluator_error,
    )
