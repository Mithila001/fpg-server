from __future__ import annotations

from typing import Any

import numpy as np

from app.algorithms.types.room import FpgRequirements

from .adapters import build_boundary, build_edges, build_nodes, initialize_positions
from .physics.engine import run_force_directed_layout
from .score.scorer import score_graph_layout
from app.algorithms.types.graph import (
    GraphBoundary,
    GraphLayoutResult,
    GraphNode,
    GraphPhysicsConfig,
)

import os
import time
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from app.core.fpg_rooms.config_fpg import TRIAL_GRAPH_SOLVER_GATE_THRESHOLD


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
    if score.total_score > TRIAL_GRAPH_SOLVER_GATE_THRESHOLD:
        plot_graph_layout(result)

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


def shrink_wrap_boundary(
    nodes: list[GraphNode],
    original_boundary: GraphBoundary,
    requested_padding: float = 10.0,
) -> GraphBoundary:
    if not nodes:
        return GraphBoundary(width=0, height=0)

    # 1. Find the raw tight bounds of the nodes
    tight_min_x = min(node.x - node.radius for node in nodes)
    tight_max_x = max(node.x + node.radius for node in nodes)
    tight_min_y = min(node.y - node.radius for node in nodes)
    tight_max_y = max(node.y + node.radius for node in nodes)

    # 2. Determine how much space we actually have available in the original container
    # We clamp the requested_padding so we don't exceed the original bounds
    pad_left = min(requested_padding, tight_min_x)
    pad_right = min(requested_padding, original_boundary.width - tight_max_x)
    pad_bottom = min(requested_padding, tight_min_y)
    pad_top = min(requested_padding, original_boundary.height - tight_max_y)

    # Ensure we don't use negative padding if nodes somehow drifted outside
    pad_left, pad_right = max(0, pad_left), max(0, pad_right)
    pad_bottom, pad_top = max(0, pad_bottom), max(0, pad_top)

    # 3. Calculate new dimensions including the allowable padding
    new_width = (tight_max_x - tight_min_x) + pad_left + pad_right
    new_height = (tight_max_y - tight_min_y) + pad_bottom + pad_top

    # 4. Shift nodes to the new coordinate system
    # They are now relative to the new (0,0) which includes the left/bottom padding
    for node in nodes:
        node.x = node.x - (tight_min_x - pad_left)
        node.y = node.y - (tight_min_y - pad_bottom)

    return GraphBoundary(width=new_width, height=new_height)


def plot_graph_layout(layout_result: "GraphLayoutResult", base_name: str = "layout"):
    """
    Plots high-fidelity graph layout with improved edge visibility and node-boundary clipping.
    """
    orig_b = layout_result.boundary
    nodes = layout_result.nodes
    requested_padding = 10.0

    # 1. Calculate the Shrunk/Padded Box
    tight_min_x = min(node.x - node.radius for node in nodes)
    tight_max_x = max(node.x + node.radius for node in nodes)
    tight_min_y = min(node.y - node.radius for node in nodes)
    tight_max_y = max(node.y + node.radius for node in nodes)

    pad_l = max(0, min(requested_padding, tight_min_x))
    pad_r = max(0, min(requested_padding, orig_b.width - tight_max_x))
    pad_b = max(0, min(requested_padding, tight_min_y))
    pad_t = max(0, min(requested_padding, orig_b.height - tight_max_y))

    shrunk_x, shrunk_y = tight_min_x - pad_l, tight_min_y - pad_b
    shrunk_w = (tight_max_x - tight_min_x) + pad_l + pad_r
    shrunk_h = (tight_max_y - tight_min_y) + pad_b + pad_t

    # 2. Setup Plotting
    output_dir = os.path.join("test", "outputs", "graph_results")
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(
        output_dir, f"{base_name}_{time.strftime('%Y%m%d-%H%M%S')}.png"
    )

    fig, ax = plt.subplots(figsize=(14, 11))

    # Expanded Styling Palette
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

    # 3. Draw Boundaries
    ax.add_patch(
        patches.Rectangle(
            (0, 0),
            orig_b.width,
            orig_b.height,
            linewidth=1,
            edgecolor="#b2bec3",
            facecolor="#f8f9fa",
            alpha=0.5,
            zorder=0,
            label="Site Boundary",
        )
    )
    ax.add_patch(
        patches.Rectangle(
            (shrunk_x, shrunk_y),
            shrunk_w,
            shrunk_h,
            linewidth=2,
            edgecolor="red",
            facecolor="none",
            linestyle="--",
            zorder=5,
            label="Padded Area",
        )
    )

    # 4. Draw Edges with Clipping and Weight Exaggeration
    node_map = {node.id: node for node in nodes}
    for edge in layout_result.edges:
        src, tgt = node_map.get(edge.source_id), node_map.get(edge.target_id)
        if src and tgt:
            # Calculate distance and unit vector to clip lines at the node circle edge
            dx, dy = tgt.x - src.x, tgt.y - src.y
            dist = np.sqrt(dx**2 + dy**2)

            if dist > (src.radius + tgt.radius):
                ux, uy = dx / dist, dy / dist
                # Start and end points shifted by radius
                x1, y1 = src.x + ux * src.radius, src.y + uy * src.radius
                x2, y2 = tgt.x - ux * tgt.radius, tgt.y - uy * tgt.radius

                # Exaggerate weight: use power of weight for higher contrast
                # 0.9 weight -> ~1.5px, 1.3 weight -> ~6px
                lw = 1.0 + (edge.weight**3) * 2
                alpha = min(0.1 + (edge.weight * 0.3), 0.7)

                # Color code by rule kind if available
                e_color = "#2980b9" if "hard" in edge.rule_kind else "#bdc3c7"

                ax.plot(
                    [x1, x2],
                    [y1, y2],
                    color=e_color,
                    linewidth=lw,
                    alpha=alpha,
                    zorder=1,
                )

    # 5. Draw Nodes
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

        # Room Label
        display_name = getattr(node, "name", node.id)
        ax.text(
            node.x,
            node.y,
            f"{display_name}\nR:{node.radius}",
            fontsize=9,
            ha="center",
            va="center",
            fontweight="bold",
            color="black" if f_color not in ["#2d3436", "#2980b9"] else "white",
            zorder=4,
        )

    # 6. Final Formatting
    ax.set_xlim(-5, orig_b.width + 5)
    ax.set_ylim(-5, orig_b.height + 5)
    ax.set_aspect("equal")

    utilization = (shrunk_w * shrunk_h) / (orig_b.width * orig_b.height) * 100
    title_str = (
        f"Layout Score: {layout_result.score.total_score:.1f} | Utilization: {utilization:.1f}%\n"
        f"Site: {orig_b.width}m x {orig_b.height}m | Design Area: {shrunk_w:.1f}m x {shrunk_h:.1f}m"
    )
    ax.set_title(title_str, loc="left", fontsize=12, fontweight="bold", pad=15)

    plt.grid(True, linestyle=":", alpha=0.4)
    plt.legend(loc="upper right", frameon=True, shadow=True)
    plt.xlabel("Width (m)")
    plt.ylabel("Height (m)")

    plt.savefig(save_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return save_path
