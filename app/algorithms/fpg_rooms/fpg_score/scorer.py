from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from app.algorithms.fpg_rooms.fpg_post_process.types import QuickPostProcessOutputPayload
from app.algorithms.fpg_rooms.types.room import FpgRequirements
from app.core.fpg_rooms.config_fpg import (
    ENVELOPE_APPLY_SIDES,
    ENVELOPE_ENABLED,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_MAX_GAP,
    ENVELOPE_MIN_GAP,
    SCORE_WEIGHTS,
)
from app.util.logger import ScoreLogger
from .metrics_coverage import score_coverage
from .metrics_empty_space import score_empty_space
from .metrics_inward_pocket import detect_inward_pocket_violation
from .metrics_rectangularity import score_rectangularity
from .types import ScoreReport
from .validators import (
    validate_adjacency_relations,
    validate_envelope_staircase_bounds,
    validate_no_overlap,
    validate_room_geometry,
)

DEFAULT_WEIGHTS = SCORE_WEIGHTS.copy()


def _coerce_room_record(raw_room: Mapping[str, Any], fallback_name: str) -> Dict[str, Any] | None:
    try:
        x = float(raw_room["x"])
        y = float(raw_room["y"])
        x_end = float(raw_room["x_end"])
        y_end = float(raw_room["y_end"])
    except (KeyError, TypeError, ValueError):
        return None

    if x_end <= x or y_end <= y:
        return None

    w = x_end - x
    h = y_end - y
    return {
        "name": str(raw_room.get("name") or fallback_name),
        "type": str(raw_room.get("type") or ""),
        "x": x,
        "y": y,
        "x_end": x_end,
        "y_end": y_end,
        "w": w,
        "h": h,
        "area": w * h,
    }


def _resolve_scoring_inputs(
    solution: Sequence[Dict[str, Any]],
    quick_post_process_result: QuickPostProcessOutputPayload | Mapping[str, Any] | None,
) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
    post_rooms: list[Mapping[str, Any]] = []
    wall_union: Dict[str, Any] = {"walls": [], "room_walls": {}}

    if isinstance(quick_post_process_result, Mapping):
        maybe_rooms = quick_post_process_result.get("rooms")
        if isinstance(maybe_rooms, list):
            post_rooms = [room for room in maybe_rooms if isinstance(room, Mapping)]

        maybe_wall_union = quick_post_process_result.get("wall_union")
        if isinstance(maybe_wall_union, Mapping):
            wall_union = {
                "walls": list(maybe_wall_union.get("walls", [])),
                "room_walls": dict(maybe_wall_union.get("room_walls", {})),
            }

    source_rooms: Sequence[Mapping[str, Any]] = post_rooms if post_rooms else solution
    normalized_rooms: list[Dict[str, Any]] = []
    for idx, room in enumerate(source_rooms):
        normalized = _coerce_room_record(room, fallback_name=f"room_{idx}")
        if normalized is not None:
            normalized_rooms.append(normalized)

    return normalized_rooms, wall_union


def score_layout(
    solution: Sequence[Dict[str, Any]],
    quick_post_process_result: QuickPostProcessOutputPayload | Mapping[str, Any] | None,
    requirements: FpgRequirements,
    min_touch_overlap: int = 1,
) -> ScoreReport:
    """Score a solved floor-plan layout.

    Hard checks (geometry, overlap, adjacency) are a gate. When a hard check
    fails, total_score becomes 0 while diagnostics are still returned.
    """
    scoring_rooms, wall_union = _resolve_scoring_inputs(solution, quick_post_process_result)
    if not scoring_rooms:
        return ScoreReport(
            valid=False,
            total_score=0.0,
            hard_violations=["Layout is empty after normalization"],
            diagnostics={},
        )

    cfg = requirements.config
    floor_width = float(cfg.floor_plan_width)
    floor_height = float(cfg.floor_plan_height)
    min_coverage = float(cfg.min_coverage)

    relation_constraints = getattr(requirements, "relation_constraints", []) or []
    weights = getattr(cfg, "score_weights", SCORE_WEIGHTS)
    if weights is None:
        weights = SCORE_WEIGHTS
    geometry_tolerance = float(getattr(cfg, "score_geometry_tolerance", 1e-6))
    inward_pocket_max_length = float(getattr(cfg, "inward_pocket_max_length", 20.0))

    hard_violations = []
    hard_violations.extend(validate_room_geometry(scoring_rooms, floor_width, floor_height))
    hard_violations.extend(validate_no_overlap(scoring_rooms))
    hard_violations.extend(
        validate_adjacency_relations(
            scoring_rooms,
            relation_constraints,
            min_overlap=min_touch_overlap,
        )
    )
    if bool(getattr(cfg, "envelope_enabled", ENVELOPE_ENABLED)):
        hard_violations.extend(
            validate_envelope_staircase_bounds(
                scoring_rooms,
                min_gap=int(getattr(cfg, "envelope_min_gap", ENVELOPE_MIN_GAP)),
                max_gap=int(getattr(cfg, "envelope_max_gap", ENVELOPE_MAX_GAP)),
                exclude_types=getattr(cfg, "envelope_exclude_types", ENVELOPE_EXCLUDE_TYPES),
                apply_sides=getattr(cfg, "envelope_apply_sides", ENVELOPE_APPLY_SIDES),
            )
        )

    empty_space_score, empty_space_diag = score_empty_space(
        scoring_rooms,
        floor_width,
        floor_height,
        wall_union=wall_union,
        tolerance=geometry_tolerance,
    )
    pocket_violation, inward_pocket_diag = detect_inward_pocket_violation(
        scoring_rooms,
        max_inward_length=inward_pocket_max_length,
        tolerance=geometry_tolerance,
    )

    geometric_gate_violations: list[str] = []
    if bool(empty_space_diag.get("has_air_gap", 0.0)):
        geometric_gate_violations.append(
            f"Air-gap detected (area={float(empty_space_diag.get('air_gap_area', 0.0)):.4f})"
        )
    if pocket_violation:
        max_segment = float(inward_pocket_diag.get("max_inward_segment_length", 0.0))
        geometric_gate_violations.append(
            f"Inward pocket segment exceeds {inward_pocket_max_length:.2f} (max={max_segment:.2f})"
        )

    diagnostics = {
        "empty_space": empty_space_diag,
        "inward_pocket": inward_pocket_diag,
        "geometric_gate_violations": geometric_gate_violations,
        "weights": weights,
    }

    valid = len(hard_violations) == 0
    if not valid:
        component_scores = {"empty_space": empty_space_score}
        ScoreLogger.score_breakdown(
            component_scores=component_scores,
            total_score=0.0,
            valid=False,
            hard_violation_count=len(hard_violations),
        )
        return ScoreReport(
            valid=False,
            total_score=0.0,
            component_scores={"empty_space": round(empty_space_score, 2)},
            hard_violations=hard_violations,
            diagnostics=diagnostics,
        )

    if geometric_gate_violations:
        component_scores = {"empty_space": empty_space_score}
        ScoreLogger.score_breakdown(
            component_scores=component_scores,
            total_score=1.0,
            valid=True,
            hard_violation_count=0,
        )
        return ScoreReport(
            valid=True,
            total_score=1.0,
            component_scores={"empty_space": round(empty_space_score, 2)},
            hard_violations=[],
            diagnostics=diagnostics,
        )

    coverage_score, coverage_diag = score_coverage(
        scoring_rooms,
        floor_width,
        floor_height,
        min_coverage,
    )
    rectangularity_score, rectangularity_diag = score_rectangularity(scoring_rooms)

    component_scores = {
        "coverage": coverage_score,
        "rectangularity": rectangularity_score,
        "empty_space": empty_space_score,
    }
    diagnostics["coverage"] = coverage_diag
    diagnostics["rectangularity"] = rectangularity_diag

    total_score = (
        component_scores["coverage"] * float(weights.get("coverage", SCORE_WEIGHTS["coverage"]))
        + component_scores["rectangularity"] * float(weights.get("rectangularity", SCORE_WEIGHTS["rectangularity"]))
        + component_scores["empty_space"] * float(weights.get("empty_space", SCORE_WEIGHTS["empty_space"]))
    )

    ScoreLogger.score_breakdown(
        component_scores=component_scores,
        total_score=total_score,
        valid=True,
        hard_violation_count=0,
    )

    return ScoreReport(
        valid=True,
        total_score=round(total_score, 2),
        component_scores={k: round(v, 2) for k, v in component_scores.items()},
        hard_violations=[],
        diagnostics=diagnostics,
    )
