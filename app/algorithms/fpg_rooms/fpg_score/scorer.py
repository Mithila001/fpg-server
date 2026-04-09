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
from .binary_scoring import (
    detect_inward_pocket_violation,
    validate_adjacency_relations,
    validate_empty_space,
    validate_envelope_staircase_bounds,
    validate_no_overlap,
    validate_room_geometry,
)
from .range_scoring import score_coverage, score_rectangularity
from .types import ScoreReport

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

    geometry_violations = validate_room_geometry(scoring_rooms, floor_width, floor_height)
    overlap_violations = validate_no_overlap(scoring_rooms)
    adjacency_violations = validate_adjacency_relations(
        scoring_rooms,
        relation_constraints,
        min_overlap=min_touch_overlap,
    )
    envelope_violations = []
    if bool(getattr(cfg, "envelope_enabled", ENVELOPE_ENABLED)):
        envelope_violations = validate_envelope_staircase_bounds(
            scoring_rooms,
            min_gap=int(getattr(cfg, "envelope_min_gap", ENVELOPE_MIN_GAP)),
            max_gap=int(getattr(cfg, "envelope_max_gap", ENVELOPE_MAX_GAP)),
            exclude_types=getattr(cfg, "envelope_exclude_types", ENVELOPE_EXCLUDE_TYPES),
            apply_sides=getattr(cfg, "envelope_apply_sides", ENVELOPE_APPLY_SIDES),
        )

    hard_violations = []
    hard_violations.extend(geometry_violations)
    hard_violations.extend(overlap_violations)
    hard_violations.extend(adjacency_violations)
    hard_violations.extend(envelope_violations)

    empty_space_violations, empty_space_diag = validate_empty_space(
        scoring_rooms,
        floor_width,
        floor_height,
        wall_union=wall_union,
        tolerance=geometry_tolerance,
    )
    hard_violations.extend(empty_space_violations)

    pocket_violation, inward_pocket_diag = detect_inward_pocket_violation(
        scoring_rooms,
        max_inward_length=inward_pocket_max_length,
        tolerance=geometry_tolerance,
    )

    geometric_gate_violations: list[str] = []
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
    room_geometry_score = not bool(geometry_violations)
    no_overlap_score = not bool(overlap_violations)
    adjacency_score = not bool(adjacency_violations)
    envelope_score = not bool(envelope_violations)
    inward_pocket_score = not bool(pocket_violation)
    empty_space_score = 100.0 if not empty_space_violations else 0.0

    if not valid:
        component_scores = {
            "coverage": 0.0,
            "rectangularity": 0.0,
            "empty_space": empty_space_score,
            "room_geometry": room_geometry_score,
            "no_overlap": no_overlap_score,
            "adjacency": adjacency_score,
            "envelope": envelope_score,
            "inward_pocket": inward_pocket_score,
        }

        return ScoreReport(
            valid=False,
            total_score=0.0,
            component_scores={"empty_space": round(empty_space_score, 2)},
            hard_violations=hard_violations,
            diagnostics=diagnostics,
        )

    if geometric_gate_violations:
        component_scores = {
            "coverage": 0.0,
            "rectangularity": 0.0,
            "empty_space": empty_space_score,
            "room_geometry": room_geometry_score,
            "no_overlap": no_overlap_score,
            "adjacency": adjacency_score,
            "envelope": envelope_score,
            "inward_pocket": inward_pocket_score,
        }
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
        "room_geometry": room_geometry_score,
        "no_overlap": no_overlap_score,
        "adjacency": adjacency_score,
        "envelope": envelope_score,
        "inward_pocket": inward_pocket_score,
    }
    diagnostics["coverage"] = coverage_diag
    diagnostics["rectangularity"] = rectangularity_diag

    total_score = (
        component_scores["coverage"] * float(weights.get("coverage", SCORE_WEIGHTS["coverage"]))
        + component_scores["rectangularity"] * float(weights.get("rectangularity", SCORE_WEIGHTS["rectangularity"]))
        + component_scores["empty_space"] * float(weights.get("empty_space", SCORE_WEIGHTS["empty_space"]))
    )

    return ScoreReport(
        valid=True,
        total_score=round(total_score, 2),
        component_scores={k: round(v, 2) for k, v in component_scores.items()},
        hard_violations=[],
        diagnostics=diagnostics,
    )
