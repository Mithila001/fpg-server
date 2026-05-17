from __future__ import annotations

from typing import List
from app.algorithms.fgp_score.score_functional.basic.basics import (
    score_basic_functional,
)
from app.algorithms.fgp_score.score_functional.path_simulations.run_path_simulation import (
    run_path_simulation,
)
from app.algorithms.types.fpg_score import (
    ScoreManagerResult,
    CheckResult,
    ScoringDiagnostics,
)

from app.algorithms.fgp_score.score_critical.adjacency_relations import (
    validate_adjacency_relations,
)
from app.algorithms.fgp_score.score_critical.empty_space import (
    validate_empty_space,
)
from app.algorithms.fgp_score.score_critical.inward_pocket import (
    detect_inward_pocket_violation_v2,
)
from app.algorithms.fgp_score.dev.critical_plot import save_critical_score_plot
from app.algorithms.types.domain import FpgRequirements
from app.algorithms.types.openings import FloorPlanWithOpenings
from app.core.fpg_rooms.config_score import SCORE_VALIDATION_MIN_OVERLAP
from app.util.verify_post_processed_floor_plan import verify_post_processed_floor_plan


def _clamp_0_25(value: float) -> float:
    return max(0.0, min(25.0, float(value)))


def score_manager(
    floor_plan_with_openings: FloorPlanWithOpenings,
    requirements: FpgRequirements,
) -> ScoreManagerResult:
    """Rectilinear gate + standalone critical scoring (out of 25).

    For now this only computes the critical section and prints results.
    """

    print("[fgp_score/score_manager1] Received FloorPlanWithOpenings for scoring.")

    # Create scoring_plan by filtering rooms while preserving openings and structure.
    # This maintains FloorPlanWithOpenings for future scoring functions that may need openings.
    filtered_rooms = [
        room
        for room in floor_plan_with_openings.floor_plan
        if room.type != "verandaOutdoorSpace" and len(room.vertices) >= 4
    ]

    scoring_plan = FloorPlanWithOpenings(
        floor_plan=filtered_rooms, openings=floor_plan_with_openings.openings
    )

    tolerance = float(getattr(requirements.config, "score_geometry_tolerance", 1e-6))
    # print(f"[fgp_score/score_manager] Floor plan for verification: {scoring_plan}")
    rectilinear_ok = verify_post_processed_floor_plan(
        scoring_plan.floor_plan, tolerance=tolerance
    )

    # print(f"\n\n[fgp_score/score_manager1] Scoring Plan: {scoring_plan}\n")

    if not rectilinear_ok:
        print(
            "\n[fgp_score/score_manager] rectilinearity verification FAILED. "
            "Returning empty ScoreManagerResult."
        )
        return ScoreManagerResult(
            critical_score=0.0,
            checks=[],
            critical_violations=[],
            diagnostics=ScoringDiagnostics(
                executed_checks=0,
                passed_checks=0,
                adjacency={"violations": []},
                empty_space={},
                inward_pocket={},
            ),
        )

    cfg = requirements.config
    floor_width = float(getattr(cfg, "floor_plan_width", 0.0))
    floor_height = float(getattr(cfg, "floor_plan_height", 0.0))
    inward_pocket_max_length = float(getattr(cfg, "inward_pocket_max_length", 20.0))
    relation_constraints = getattr(requirements, "relation_constraints", []) or []

    # --- Critical checks (each contributes 1 slot out of 25) ---
    adjacency_violations = validate_adjacency_relations(
        scoring_plan.floor_plan,
        relation_constraints,
        min_overlap=int(SCORE_VALIDATION_MIN_OVERLAP),
        tolerance=tolerance,
    )
    adjacency_passed = len(adjacency_violations) == 0

    empty_violations, empty_diag = validate_empty_space(
        scoring_plan.floor_plan,
        floor_width,
        floor_height,
        tolerance=tolerance,
    )
    empty_passed = len(empty_violations) == 0

    pocket_violation, inward_diag = detect_inward_pocket_violation_v2(
        scoring_plan.floor_plan,
        max_inward_length=inward_pocket_max_length,
        tolerance=tolerance,
    )
    inward_passed = not pocket_violation
    inward_violations: list[str]
    if inward_passed:
        inward_violations = []
    else:
        max_delta = float(inward_diag.get("max_inward_segment_length", 0.0))
        inward_violations = [
            "Inward pocket violation detected "
            f"(max_delta={max_delta:.2f}, threshold={inward_pocket_max_length:.2f})"
        ]
    # --- Path simulation (dev/testing only — does not affect scoring) ---
    # try:
    #     path_result = run_path_simulation(scoring_plan)
    #     print(
    #         f"\n[fgp_score/score_manager] path_simulation done: "
    #         f"score={path_result.total_score:.1f}  "
    #         f"paths={len(path_result.paths)}  "
    #         f"plot={path_result.plot_path}"
    #     )
    # except Exception as _path_exc:
    #     print(f"[fgp_score/score_manager] path_simulation ERROR: {_path_exc}")
    #     import traceback

    # traceback.print_exc()
    checks: List[CheckResult] = [
        CheckResult(
            name="adjacency_relations",
            passed=adjacency_passed,
            violations=adjacency_violations,
        ),
        CheckResult(
            name="empty_space", passed=empty_passed, violations=empty_violations
        ),
        CheckResult(
            name="inward_pocket", passed=inward_passed, violations=inward_violations
        ),
    ]

    critical_violations: List[str] = []
    passed_checks = 0
    for check in checks:
        if check.passed:
            passed_checks += 1
        else:
            critical_violations.extend(list(check.violations or []))

    total_checks = len(checks)
    critical_score = _clamp_0_25(
        (25.0 * passed_checks / total_checks) if total_checks > 0 else 0.0
    )

    # --- Printing (explicit + stable keys for manual debugging) ---
    print(
        "\n[fgp_score/score_manager] critical_report "
        f"critical_score={critical_score:.2f} "
        f"passed={passed_checks}/{total_checks}"
    )
    for check in checks:
        print(
            f"[fgp_score/score_manager] check={check.name} "
            f"passed={check.passed} violations={len(check.violations)}"
        )

    diagnostics = ScoringDiagnostics(
        executed_checks=total_checks,
        passed_checks=passed_checks,
        adjacency={"violations": adjacency_violations},
        empty_space=empty_diag,
        inward_pocket=inward_diag,
    )

    # try:
    #     critical_plot_path = save_critical_score_plot(
    #         scoring_plan.floor_plan,
    #         relation_constraints,
    #         floor_width,
    #         floor_height,
    #         inward_pocket_max_length,
    #         min_overlap=int(SCORE_VALIDATION_MIN_OVERLAP),
    #         tolerance=tolerance,
    #     )
    #     diagnostics.critical_plot_path = critical_plot_path
    #     print(f"[fgp_score/score_manager] critical plot saved: {critical_plot_path}")
    # except Exception as exc:
    #     print(f"[fgp_score/score_manager] critical plot generation failed: {exc}")

    final_score = 0

    # TODO REMOVE THIS LATER
    if critical_score == 25:
        functional_score = score_basic_functional(scoring_plan, 75)
        final_score = critical_score + functional_score
    else:
        final_score = critical_score

    return ScoreManagerResult(
        critical_score=round(float(final_score), 2),
        checks=checks,
        critical_violations=critical_violations,
        diagnostics=diagnostics,
    )
