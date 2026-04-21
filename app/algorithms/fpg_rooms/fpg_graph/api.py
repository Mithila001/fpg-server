from __future__ import annotations

from typing import Any

from app.algorithms.fpg_rooms.types.room import FpgRequirements

from .adapters import build_boundary, build_edges, build_nodes, initialize_positions
from .physics.engine import run_force_directed_layout
from .score.scorer import score_graph_layout
from .types import GraphLayoutResult, GraphPhysicsConfig


def run_graph_layout(
    requirements: FpgRequirements,
    hallway_count_override: int | None = None,
    seed: int | None = None,
    relation_constraints: list[Any] | None = None,
    physics_config: GraphPhysicsConfig | None = None,
) -> GraphLayoutResult:
    boundary = build_boundary(requirements)
    nodes = build_nodes(requirements, hallway_count_override=hallway_count_override)

    relations = relation_constraints
    if relations is None:
        relations = list(requirements.relation_constraints)

    edges = build_edges(nodes, relations)
    initialize_positions(nodes, boundary, seed=seed)

    config = physics_config or GraphPhysicsConfig()
    convergence = run_force_directed_layout(
        nodes=nodes,
        edges=edges,
        boundary=boundary,
        config=config,
    )

    score = score_graph_layout(
        nodes=nodes,
        edges=edges,
        relation_constraints=relations,
    )

    return GraphLayoutResult(
        nodes=nodes,
        edges=edges,
        boundary=boundary,
        convergence=convergence,
        score=score,
        diagnostics={
            "node_count": len(nodes),
            "edge_count": len(edges),
            "converged": convergence.converged,
            "iterations_run": convergence.iterations_run,
        },
    )
