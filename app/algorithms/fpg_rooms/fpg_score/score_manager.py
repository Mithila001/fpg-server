from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence

from app.algorithms.types import (
    QuickPostProcessOutputPayload,
    FpgRequirements,
)
from app.algorithms.fpg_rooms.fpg_score.score_critical.inward_pocket import (
    detect_inward_pocket_violation_v2,
)
from app.core.fpg_rooms.config_fpg import (
    ENVELOPE_APPLY_SIDES,
    ENVELOPE_ENABLED,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_MAX_GAP,
    ENVELOPE_MIN_GAP,
    SCORE_WEIGHTS,
)
from .score_critical import (
    detect_inward_pocket_violation,
    validate_adjacency_relations,
    validate_empty_space,
    validate_envelope_staircase_bounds,
    validate_no_overlap,
    validate_room_geometry,
)
from .score_extra import score_extra_section
from .score_functional import score_functional_section
from .score_room import score_coverage, score_rectangularity
from .types import ScoreReport
from app.util.logger.system_logger import SystemLogger


DEFAULT_WEIGHTS = SCORE_WEIGHTS.copy()


def _coerce_room_record(
    raw_room: Mapping[str, Any], fallback_name: str
) -> Dict[str, Any] | None:
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
) -> tuple[list[Dict[str, Any]], Dict[str, Any], list[Dict[str, Any]]]:
    post_rooms: list[Mapping[str, Any]] = []
    wall_union: Dict[str, Any] = {"walls": [], "room_walls": {}}
    openings: list[Dict[str, Any]] = []

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

        maybe_openings = quick_post_process_result.get("openings")
        if isinstance(maybe_openings, list):
            openings = [
                opening for opening in maybe_openings if isinstance(opening, Mapping)
            ]

    source_rooms: Sequence[Mapping[str, Any]] = post_rooms if post_rooms else solution
    normalized_rooms: list[Dict[str, Any]] = []
    for idx, room in enumerate(source_rooms):
        normalized = _coerce_room_record(room, fallback_name=f"room_{idx}")
        if normalized is not None:
            normalized_rooms.append(normalized)

    return normalized_rooms, wall_union, [dict(opening) for opening in openings]


def _clamp_0_25(value: float) -> float:
    return max(0.0, min(25.0, float(value)))


def _score_critical_section(
    scoring_rooms: Sequence[Dict[str, Any]],
    requirements: FpgRequirements,
    floor_width: float,
    floor_height: float,
    wall_union: Dict[str, Any],
    min_touch_overlap: int,
) -> Dict[str, Any]:
    cfg = requirements.config
    relation_constraints = getattr(requirements, "relation_constraints", []) or []
    geometry_tolerance = float(getattr(cfg, "score_geometry_tolerance", 1e-6))
    inward_pocket_max_length = float(getattr(cfg, "inward_pocket_max_length", 20.0))

    checks: list[Dict[str, Any]] = []
    critical_violations: list[str] = []

    def _append_check(name: str, violations: Sequence[str]) -> None:
        passed = len(violations) == 0
        checks.append(
            {
                "name": name,
                "passed": passed,
                "violations": list(violations),
            }
        )
        if not passed:
            critical_violations.extend(violations)

    geometry_violations = validate_room_geometry(
        scoring_rooms, floor_width, floor_height
    )
    _append_check("room_geometry", geometry_violations)

    overlap_violations = validate_no_overlap(scoring_rooms)
    _append_check("no_overlap", overlap_violations)

    adjacency_violations = validate_adjacency_relations(
        scoring_rooms,
        relation_constraints,
        min_overlap=min_touch_overlap,
    )
    _append_check("adjacency_relations", adjacency_violations)

    envelope_enabled = bool(getattr(cfg, "envelope_enabled", ENVELOPE_ENABLED))
    if envelope_enabled:
        envelope_violations = validate_envelope_staircase_bounds(
            scoring_rooms,
            min_gap=int(getattr(cfg, "envelope_min_gap", ENVELOPE_MIN_GAP)),
            max_gap=int(getattr(cfg, "envelope_max_gap", ENVELOPE_MAX_GAP)),
            exclude_types=getattr(
                cfg, "envelope_exclude_types", ENVELOPE_EXCLUDE_TYPES
            ),
            apply_sides=getattr(cfg, "envelope_apply_sides", ENVELOPE_APPLY_SIDES),
        )
        _append_check("envelope_staircase_bounds", envelope_violations)

    empty_space_violations, empty_space_diag = validate_empty_space(
        scoring_rooms,
        floor_width,
        floor_height,
        wall_union=wall_union,
        tolerance=geometry_tolerance,
    )
    _append_check("empty_space", empty_space_violations)

    pocket_violation, inward_pocket_diag = detect_inward_pocket_violation_v2(
        scoring_rooms,
        max_inward_length=inward_pocket_max_length,
        tolerance=geometry_tolerance,
    )
    inward_pocket_violations: list[str] = []
    if pocket_violation:
        max_segment = float(inward_pocket_diag.get("max_inward_segment_length", 0.0))
        inward_pocket_violations.append(
            f"Inward pocket segment exceeds {inward_pocket_max_length:.2f} (max={max_segment:.2f})"
        )
    _append_check("inward_pocket", inward_pocket_violations)

    total_checks = len(checks)
    passed_checks = sum(1 for check in checks if bool(check["passed"]))
    critical_score = _clamp_0_25(
        (25.0 * passed_checks / total_checks) if total_checks > 0 else 0.0
    )

    SystemLogger.log_event(
        tag="SCORE",
        event="score_critical",
        level="INFO",
        data={
            "critical_score": round(critical_score, 2),
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "checks": [
                {"name": check["name"], "passed": check["passed"]} for check in checks
            ],
        },
    )

    return {
        "score": critical_score,
        "checks": checks,
        "critical_violations": critical_violations,
        "diagnostics": {
            "executed_checks": total_checks,
            "passed_checks": passed_checks,
            "empty_space": empty_space_diag,
            "inward_pocket": inward_pocket_diag,
        },
    }


def _score_room_section(
    scoring_rooms: Sequence[Dict[str, Any]],
    floor_width: float,
    floor_height: float,
    min_coverage: float,
    weights: Mapping[str, float],
) -> Dict[str, Any]:
    coverage_score, coverage_diag = score_coverage(
        scoring_rooms,
        floor_width,
        floor_height,
        min_coverage,
    )
    rectangularity_score, rectangularity_diag = score_rectangularity(scoring_rooms)

    coverage_weight = float(weights.get("coverage", SCORE_WEIGHTS.get("coverage", 1.0)))
    rectangularity_weight = float(
        weights.get("rectangularity", SCORE_WEIGHTS.get("rectangularity", 1.0))
    )
    weight_total = coverage_weight + rectangularity_weight
    if weight_total <= 0:
        coverage_weight = 1.0
        rectangularity_weight = 1.0
        weight_total = 2.0

    weighted_average = (
        (coverage_score * coverage_weight)
        + (rectangularity_score * rectangularity_weight)
    ) / weight_total
    room_score = _clamp_0_25((weighted_average / 100.0) * 25.0)

    SystemLogger.log_event(
        tag="SCORE",
        event="score_room",
        level="INFO",
        data={
            "room_score": round(room_score, 2),
            "coverage_score": round(coverage_score, 2),
            "rectangularity_score": round(rectangularity_score, 2),
            "weighted_average": round(weighted_average, 2),
            "weights": {
                "coverage": coverage_weight,
                "rectangularity": rectangularity_weight,
            },
        },
    )

    return {
        "score": room_score,
        "coverage_score": coverage_score,
        "rectangularity_score": rectangularity_score,
        "diagnostics": {
            "coverage": coverage_diag,
            "rectangularity": rectangularity_diag,
            "weighted_average": weighted_average,
            "weights": {
                "coverage": coverage_weight,
                "rectangularity": rectangularity_weight,
            },
        },
    }


def score_layout(
    solution: Sequence[Dict[str, Any]],
    quick_post_process_result: QuickPostProcessOutputPayload | Mapping[str, Any] | None,
    requirements: FpgRequirements,
    min_touch_overlap: int = 1,
) -> ScoreReport:
    """Score a solved floor-plan layout using 4 sections with two gate rules."""
    scoring_rooms, wall_union, openings = _resolve_scoring_inputs(
        solution, quick_post_process_result
    )
    if not scoring_rooms:
        print("\n[score_manager] no scoring rooms after normalization")
        SystemLogger.log_event(
            tag="SCORE",
            event="score_no_rooms",
            level="INFO",
            data={
                "reason": "no_scoring_rooms",
                "solution_length": len(solution),
                "normalized_room_count": len(scoring_rooms),
            },
        )
        return ScoreReport(
            valid=False,
            total_score=0.0,
            component_scores={
                "critical": 0.0,
                "room": 0.0,
                "functional": 0.0,
                "extra": 0.0,
            },
            hard_violations=["Layout is empty after normalization"],
            diagnostics={},
        )

    cfg = requirements.config
    floor_width = float(cfg.floor_plan_width)
    floor_height = float(cfg.floor_plan_height)
    min_coverage = float(cfg.min_coverage)
    weights = getattr(cfg, "score_weights", SCORE_WEIGHTS)
    if weights is None:
        weights = SCORE_WEIGHTS

    critical_result = _score_critical_section(
        scoring_rooms=scoring_rooms,
        requirements=requirements,
        floor_width=floor_width,
        floor_height=floor_height,
        wall_union=wall_union,
        min_touch_overlap=min_touch_overlap,
    )
    critical_score = float(critical_result["score"])
    critical_full = math.isclose(critical_score, 25.0, abs_tol=1e-6)

    print(
        f"\n[score_manager] critical section: score={critical_score}, "
        f"passed={critical_result['diagnostics']['passed_checks']}/"
        f"{critical_result['diagnostics']['executed_checks']}"
    )

    component_scores: Dict[str, float] = {
        "critical": round(critical_score, 2),
        "room": 0.0,
        "functional": 0.0,
        "extra": 0.0,
    }
    diagnostics = {
        "critical": critical_result["diagnostics"],
        "critical_checks": critical_result["checks"],
        "openings_count": len(openings),
        "gates": {
            "critical_full": critical_full,
            "critical_room_threshold_passed": False,
        },
    }

    if not critical_full:
        print(
            f"\n[score_manager] gating out remaining sections because critical < 25: "
            f"{critical_score}"
        )
        SystemLogger.log_event(
            tag="SCORE",
            event="low score_critical : Stopped",
            level="INFO",
            data={
                "critical_score": round(critical_score, 2),
                "passed_checks": critical_result["diagnostics"]["passed_checks"],
                "total_checks": critical_result["diagnostics"]["executed_checks"],
                "failed_checks": [
                    check["name"]
                    for check in critical_result["checks"]
                    if not check["passed"]
                ],
            },
        )
        return ScoreReport(
            valid=False,
            total_score=round(critical_score, 2),
            component_scores=component_scores,
            hard_violations=list(critical_result["critical_violations"]),
            diagnostics=diagnostics,
        )

    room_result = _score_room_section(
        scoring_rooms=scoring_rooms,
        floor_width=floor_width,
        floor_height=floor_height,
        min_coverage=min_coverage,
        weights=weights,
    )
    room_score = float(room_result["score"])
    component_scores["room"] = round(room_score, 2)
    component_scores["room_coverage_raw"] = round(
        float(room_result["coverage_score"]), 2
    )
    component_scores["room_rectangularity_raw"] = round(
        float(room_result["rectangularity_score"]),
        2,
    )
    diagnostics["room"] = room_result["diagnostics"]

    critical_room_total = critical_score + room_score
    critical_room_threshold_passed = critical_room_total >= 40.0
    diagnostics["gates"]["critical_room_threshold_passed"] = (
        critical_room_threshold_passed
    )
    diagnostics["gates"]["critical_room_total"] = round(critical_room_total, 2)

    print(
        f"\n[score_manager] room section: score={room_score}, "
        f"critical_room_total={critical_room_total}, gate2_passed={critical_room_threshold_passed}"
    )

    if not critical_room_threshold_passed:
        print(
            "\n[score_manager] gating out functional and extra because critical+room < 40"
        )
        SystemLogger.log_event(
            tag="SCORE",
            event="score_gate_blocked",
            level="INFO",
            data={
                "reason": "critical_room_below_threshold",
                "critical_score": round(critical_score, 2),
                "room_score": round(room_score, 2),
                "critical_room_total": round(critical_room_total, 2),
                "threshold": 40.0,
            },
        )
        return ScoreReport(
            valid=True,
            total_score=round(critical_room_total, 2),
            component_scores=component_scores,
            hard_violations=[],
            diagnostics=diagnostics,
        )

    functional_score, functional_diag = score_functional_section(
        scoring_rooms,
        openings=openings,
    )

    SystemLogger.log_event(
        tag="SCORE",
        event="score_functional",
        level="INFO",
        data={
            "functional_diag": functional_diag,  # sym:functional_diag
            "opening_scores": [
                {"name": evaluator["name"], "score": evaluator["score"]}
                for evaluator in functional_diag.get("evaluators", [])
            ],
        },
    )

    extra_score, extra_diag = score_extra_section(scoring_rooms)

    component_scores["functional"] = round(float(functional_score), 2)
    component_scores["extra"] = round(float(extra_score), 2)
    diagnostics["functional"] = functional_diag
    diagnostics["extra"] = extra_diag

    print(
        f"\n[score_manager] functional section: score={functional_score}, extra section: score={extra_score}"
    )

    total_score = (
        critical_score + room_score + float(functional_score) + float(extra_score)
    )

    SystemLogger.log_event(
        tag="SCORE",
        event="score_complete",
        level="INFO",
        data={
            "total_score": round(total_score, 2),
            "critical_score": round(critical_score, 2),
            "room_score": round(room_score, 2),
            "functional_score": round(float(functional_score), 2),
            "extra_score": round(float(extra_score), 2),
        },
    )

    return ScoreReport(
        valid=True,
        total_score=round(total_score, 2),
        component_scores=component_scores,
        hard_violations=[],
        diagnostics=diagnostics,
    )
