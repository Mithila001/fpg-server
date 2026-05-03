from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.algorithms.types import FpgRequirements
from app.core.fpg_rooms.config_fpg import (
    TRIAL_GRAPH_SOLVER_GATE_THRESHOLD,
    OPTUNA_SEARCH_SPACE_GRID_SCALE,
)
from pathlib import Path

from .dev.plotters import save_relation_graph_plot, save_relation_path_plot
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

    print(f"Hallway Count: {requirements.config.hallway_count}")

    # print(
    #     f"Room points: {[f'{p.name}({p.room_type}): ({p.x:.1f}, {p.y:.1f})' for p in room_points]}"
    # )

    zone_result = score_floor_plan_zones(requirements, room_points)
    print(
        f"\nZone Score: {zone_result.score:.1f}/{zone_result.max_score} , \nDetails: {zone_result.details}\n"
    )
    clearance_result: SectionScore = score_outer_clearance(requirements, room_points)
    relation_result = score_room_relations(requirements, room_points)
    section_scores = {
        "floor_plan_zones": zone_result.score,
        "outer_clearance": clearance_result.score,
        "room_relations": relation_result.score,
    }
    print(
        f"Untouched Hallways: {relation_result.details.get('uncrossed_hallways', [])}"
    )
    print(f"Section Scores: {section_scores}")
    print(f"Clearance Score: {clearance_result.score:.1f}/{clearance_result.max_score}")
    print(
        " | ".join(
            [
                f"{k.replace('_', ' ').title()}: {v:.1f}/{m}"
                for k, v, m in zip(
                    section_scores.keys(), section_scores.values(), [30, 20, 40]
                )
            ]
        )
    )
    total_score = sum(section_scores.values())
    print(f"Total Score: {total_score:.1f}/90.0")
    usable_layout = total_score >= float(TRIAL_GRAPH_SOLVER_GATE_THRESHOLD)

    # Save relation plots when requested and score passes the gate threshold
    if save_debug_plots and total_score > TRIAL_GRAPH_SOLVER_GATE_THRESHOLD:
        try:
            print("Saving room relation graph and path plots...")
            output_root = Path("test/outputs/optuna_score")
            details = relation_result.details or {}
            graph = details.get("graph")
            path_summaries = details.get("path_summaries", [])
            if graph is not None:
                floor_width = float(requirements.config.floor_plan_width)
                floor_height = float(requirements.config.floor_plan_height)
                save_relation_graph_plot(
                    graph,
                    room_points,
                    output_root / "graph",
                    floor_width=floor_width,
                    floor_height=floor_height,
                    grid_scale=OPTUNA_SEARCH_SPACE_GRID_SCALE,
                )
                save_relation_path_plot(
                    graph,
                    room_points,
                    path_summaries,
                    output_root / "pathing",
                    floor_width=floor_width,
                    floor_height=floor_height,
                )
        except Exception:
            # avoid breaking scoring if plotting fails
            pass

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
