from __future__ import annotations

from typing import Any

from app.core.fpg_rooms.config_fpg import TRIAL_GRAPH_SOLVER_GATE_THRESHOLD

from .hard_score.h_outer_clearance import evaluate_outer_clearance_hard
from .hard_score.h_room_location import evaluate_room_location_hard
from .soft_score.s_room_location import evaluate_room_location_soft
from ..types import GraphEdge, GraphNode, GraphScoreBreakdown


def _layout_bounds(nodes: list[GraphNode]) -> tuple[float, float, float, float]:
    if not nodes:
        return 0.0, 0.0, 1.0, 1.0

    min_x = min(node.x - node.radius for node in nodes)
    max_x = max(node.x + node.radius for node in nodes)
    min_y = min(node.y - node.radius for node in nodes)
    max_y = max(node.y + node.radius for node in nodes)

    width = max(1e-6, max_x - min_x)
    height = max(1e-6, max_y - min_y)
    return min_x, min_y, width, height


def score_graph_layout(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    relation_constraints: list[Any],
) -> GraphScoreBreakdown:
    del edges, relation_constraints

    min_x, min_y, width, height = _layout_bounds(nodes)

    hard_results: dict[str, bool] = {}
    hard_results.update(evaluate_room_location_hard(nodes, min_x, min_y, width, height))
    hard_results.update(evaluate_outer_clearance_hard(nodes))

    hard_total = len(hard_results)
    hard_passed = sum(1 for passed in hard_results.values() if passed)
    hard_score = (hard_passed / hard_total) * 40.0 if hard_total > 0 else 0.0

    soft_results = evaluate_room_location_soft(nodes, min_x, min_y, width, height)
    soft_score = sum(soft_results.values())
    soft_score = max(0.0, min(50.0, soft_score))

    total_score = hard_score + soft_score
    usable_layout = total_score >= float(TRIAL_GRAPH_SOLVER_GATE_THRESHOLD)

    return GraphScoreBreakdown(
        hard_score=hard_score,
        soft_score=soft_score,
        total_score=total_score,
        usable_layout=usable_layout,
        hard_passed=hard_passed,
        hard_total=hard_total,
        hard_results=hard_results,
        soft_results=soft_results,
    )
