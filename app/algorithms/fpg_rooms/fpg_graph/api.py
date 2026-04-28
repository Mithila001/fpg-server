from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any

from app.algorithms.types import FpgRequirements
from app.algorithms.types.solvers import (
    GraphLayoutResult,
    GraphPhysicsConfig,
)
from app.core.fpg_rooms.config_fpg import TRIAL_GRAPH_SOLVER_GATE_THRESHOLD

from .adapters import build_boundary, build_edges, build_nodes, initialize_positions
from .physics.engine import run_force_directed_layout
from .score.scorer import score_graph_layout


def _with_iterations(config: GraphPhysicsConfig, iterations: int) -> GraphPhysicsConfig:
    return replace(
        config,
        iterations=max(1, int(iterations)),
        use_staged_node_sizing=False,
    )


def run_graph_layout(
    requirements: FpgRequirements,
    seed: int | None = None,
    explicit_positions: dict[str, tuple[float, float]] | None = None,
    relation_constraints: list[Any] | None = None,
    physics_config: GraphPhysicsConfig | None = None,
    plot_base_name: str = "layout_comparison",
) -> GraphLayoutResult:
    boundary = build_boundary(requirements)

    nodes = build_nodes(requirements)

    relations = relation_constraints
    if relations is None:
        relations = list(requirements.relation_constraints)

    edges = build_edges(nodes, relations)
    initialize_positions(
        nodes, boundary, seed=seed, explicit_positions=explicit_positions
    )

    # Capture initial state before physics engine modifies node positions
    initial_nodes = copy.deepcopy(nodes)

    config = physics_config or GraphPhysicsConfig()

    staged_sizing_used = False
    stage1_convergence = None
    stage2_convergence = None
    phase1_nodes = None

    if config.use_staged_node_sizing and config.staged_uniform_radius > 0.0:
        staged_sizing_used = True
        original_radii = {node.id: node.radius for node in nodes}
        uniform_radius = float(config.staged_uniform_radius)

        for node in nodes:
            node.radius = uniform_radius

        stage1_convergence = run_force_directed_layout(
            nodes=nodes,
            edges=edges,
            boundary=boundary,
            config=_with_iterations(config, config.staged_phase1_iterations),
        )
        phase1_nodes = copy.deepcopy(nodes)

        # Inflate back to target room sizes, then settle.
        for node in nodes:
            node.radius = original_radii.get(node.id, node.radius)
            node.vx = 0.0
            node.vy = 0.0

        stage2_convergence = run_force_directed_layout(
            nodes=nodes,
            edges=edges,
            boundary=boundary,
            config=_with_iterations(config, config.staged_phase2_iterations),
        )
        convergence = stage2_convergence
    else:
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

    result = GraphLayoutResult(
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
            "staged_sizing_used": staged_sizing_used,
            "stage1_iterations_run": (
                stage1_convergence.iterations_run if stage1_convergence else 0
            ),
            "stage2_iterations_run": (
                stage2_convergence.iterations_run if stage2_convergence else 0
            ),
            "stage1_converged": (
                bool(stage1_convergence.converged) if stage1_convergence else False
            ),
            "stage2_converged": (
                bool(stage2_convergence.converged) if stage2_convergence else False
            ),
        },
    )

    if  score.total_score > TRIAL_GRAPH_SOLVER_GATE_THRESHOLD:
        try:
            from test.dev.graph_plotter import plot_graph_layout

            plot_graph_layout(
                layout_result=result,
                initial_nodes=initial_nodes,
                phase1_nodes=phase1_nodes,
                base_name=plot_base_name,
            )
        except Exception:
            pass

    return result
