from __future__ import annotations

import copy
import os
import time
from typing import Any

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np

from app.algorithms.types import FpgRequirements
from app.algorithms.types.solvers import (
    GraphBoundary,
    GraphLayoutResult,
    GraphNode,
    GraphPhysicsConfig,
)
from app.core.fpg_rooms.config_fpg import TRIAL_GRAPH_SOLVER_GATE_THRESHOLD

from .adapters import build_boundary, build_edges, build_nodes, initialize_positions
from .physics.engine import run_force_directed_layout
from .score.scorer import score_graph_layout


def run_graph_layout(
    requirements: FpgRequirements,
    hallway_count_override: int | None = None,
    seed: int | None = None,
    explicit_positions: dict[str, tuple[float, float]] | None = None,
    relation_constraints: list[Any] | None = None,
    physics_config: GraphPhysicsConfig | None = None,
) -> GraphLayoutResult:
    boundary = build_boundary(requirements)
    nodes = build_nodes(requirements, hallway_count_override=hallway_count_override)

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
        },
    )

    # Pass the initial state to the plotter for comparison
    if score.total_score > TRIAL_GRAPH_SOLVER_GATE_THRESHOLD:
        plot_graph_layout(result, initial_nodes=initial_nodes)

    return result


def plot_graph_layout(
    layout_result: GraphLayoutResult,
    initial_nodes: list[GraphNode] | None = None,
    base_name: str = "layout_comparison",
) -> str:
    """
    Plots a side-by-side comparison: Initial Layout vs Physics-Optimized Layout.
    """
    output_dir = os.path.join("test", "outputs", "graph_results")
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(
        output_dir, f"{base_name}_{time.strftime('%Y%m%d-%H%M%S')}.png"
    )

    # Setup the Side-by-Side figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 11))

    colors = {
        "hallway": "#95a5a6",
        "kitchen": "#f1c40f",
        "livingRoom": "#3498db",
        "diningRoom": "#e67e22",
        "bedroom": "#a29bfe",
        "garage": "#2d3436",
        "veranda": "#26de81",
        "bathroom": "#81ecec",
        "attachedBathroom": "#74b9ff",
    }
    default_color = "#dfe6e9"

    def _draw_on_axis(ax: plt.Axes, nodes: list[GraphNode], title: str):  # type: ignore
        # 1. Draw Site Boundary
        ax.add_patch(
            patches.Rectangle(
                (0, 0),
                layout_result.boundary.width,
                layout_result.boundary.height,
                linewidth=1,
                edgecolor="#b2bec3",
                facecolor="#f8f9fa",
                alpha=0.5,
                zorder=0,
            )
        )

        # 2. Draw Edges (Clipping logic)
        node_map = {node.id: node for node in nodes}
        for edge in layout_result.edges:
            src, tgt = node_map.get(edge.source_id), node_map.get(edge.target_id)
            if src and tgt:
                dx, dy = tgt.x - src.x, tgt.y - src.y
                dist = np.sqrt(dx**2 + dy**2)
                if dist > (src.radius + tgt.radius):
                    ux, uy = dx / dist, dy / dist
                    x1, y1 = src.x + ux * src.radius, src.y + uy * src.radius
                    x2, y2 = tgt.x - ux * tgt.radius, tgt.y - uy * tgt.radius

                    lw = 1.0 + (edge.weight**3) * 2
                    alpha = min(0.1 + (edge.weight * 0.3), 0.7)
                    e_color = "#2980b9" if "hard" in edge.rule_kind else "#bdc3c7"

                    ax.plot(
                        [x1, x2],
                        [y1, y2],
                        color=e_color,
                        linewidth=lw,
                        alpha=alpha,
                        zorder=1,
                    )

        # 3. Draw Nodes
        for node in nodes:
            f_color = colors.get(node.room_type, default_color)
            e_style = "--" if getattr(node, "synthesized", False) else "-"
            ax.add_patch(
                patches.Circle(
                    (node.x, node.y),
                    node.radius,
                    linewidth=2,
                    edgecolor="#2d3436",
                    facecolor=f_color,
                    linestyle=e_style,
                    alpha=0.9,
                    zorder=3,
                )
            )

            display_name = getattr(node, "name", node.id)
            ax.text(
                node.x,
                node.y,
                f"{display_name}\nR:{node.radius}",
                fontsize=8,
                ha="center",
                va="center",
                fontweight="bold",
                color="black" if f_color not in ["#2d3436", "#2980b9"] else "white",
                zorder=4,
            )

        ax.set_xlim(-5, layout_result.boundary.width + 5)
        ax.set_ylim(-5, layout_result.boundary.height + 5)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.4)

    # Draw Left: Initial State
    if initial_nodes:
        _draw_on_axis(ax1, initial_nodes, "INITIAL STATE (Pre-Physics)")
    else:
        ax1.text(
            0.5, 0.5, "No Initial Data Provided", ha="center", transform=ax1.transAxes
        )

    # Draw Right: Final State
    _draw_on_axis(
        ax2,
        layout_result.nodes,
        f"FINAL STATE (Score: {layout_result.score.total_score:.1f})",
    )

    # Final Overall Labeling
    fig.suptitle(
        f"Graph Layout Evolution | {layout_result.boundary.width}m x {layout_result.boundary.height}m",
        fontsize=18,
        fontweight="bold",
        y=0.95,
    )

    # Fix: rect must be a tuple, not a list
    plt.tight_layout(rect=(0, 0.03, 1, 0.95))
    plt.savefig(save_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return save_path
