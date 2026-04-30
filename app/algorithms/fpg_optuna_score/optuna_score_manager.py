from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.algorithms.types import FpgRequirements
from app.core.fpg_rooms.config_fpg import TRIAL_GRAPH_SOLVER_GATE_THRESHOLD

from .score import score_floor_plan_zones, score_outer_clearance, score_room_relations
from .util.scoring_common import OptunaScorePoint, SectionScore, build_room_points


@dataclass
class OptunaScoreResult:
    total_score: float
    usable_layout: bool
    section_scores: dict[str, float] = field(default_factory=dict)
    section_results: dict[str, SectionScore] = field(default_factory=dict)
    room_points: list[OptunaScorePoint] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def score_optuna_layout(
    requirements: FpgRequirements,
    sampled_positions: Mapping[str, Any],
    *,
    save_debug_plots: bool = False,
) -> OptunaScoreResult:
    room_points = build_room_points(requirements, sampled_positions)

    zone_result = score_floor_plan_zones(requirements, room_points)
    clearance_result = score_outer_clearance(requirements, room_points)
    relation_result = score_room_relations(
        requirements,
        room_points,
        save_plots=save_debug_plots,
    )
    print(f"Requirements: {requirements}")
    print(f"Sampled Positions: {sampled_positions}")
    print(f"Room Points: {room_points}")
    section_scores = {
        "floor_plan_zones": zone_result.score,
        "outer_clearance": clearance_result.score,
        "room_relations": relation_result.score,
    }
    total_score = sum(section_scores.values())
    usable_layout = total_score >= float(TRIAL_GRAPH_SOLVER_GATE_THRESHOLD)

    diagnostics = {
        "floor_plan_zones": zone_result.details,
        "outer_clearance": clearance_result.details,
        "room_relations": relation_result.details,
        "warnings": {
            "floor_plan_zones": zone_result.warnings,
            "outer_clearance": clearance_result.warnings,
            "room_relations": relation_result.warnings,
        },
    }

    return OptunaScoreResult(
        total_score=total_score,
        usable_layout=usable_layout,
        section_scores=section_scores,
        section_results={
            "floor_plan_zones": zone_result,
            "outer_clearance": clearance_result,
            "room_relations": relation_result,
        },
        room_points=room_points,
        diagnostics=diagnostics,
    )