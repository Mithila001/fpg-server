from __future__ import annotations

from typing import Any

from .score_manager import score_graph_layout as _score_graph_layout
from app.algorithms.types.solvers import GraphEdge, GraphNode, GraphScoreBreakdown


def score_graph_layout(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    relation_constraints: list[Any],
) -> GraphScoreBreakdown:
    return _score_graph_layout(
        nodes=nodes, edges=edges, relation_constraints=relation_constraints
    )
