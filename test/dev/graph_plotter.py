from __future__ import annotations

import os
import time
from typing import Any

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np

from app.algorithms.types.solvers import GraphLayoutResult, GraphNode
from app.util.tracking import get_tracking_ids


def _draw_on_axis(
    ax: Any,
    layout_result: GraphLayoutResult,
    nodes: list[GraphNode],
    title: str,
) -> None:
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

    # Draw site boundary first so all geometry is relative to the floor plan.
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

    node_map = {node.id: node for node in nodes}
    for edge in layout_result.edges:
        src, tgt = node_map.get(edge.source_id), node_map.get(edge.target_id)
        if src is None or tgt is None:
            continue

        dx, dy = tgt.x - src.x, tgt.y - src.y
        dist = np.sqrt(dx**2 + dy**2)
        if dist <= (src.radius + tgt.radius):
            continue

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


def plot_graph_layout(
    layout_result: GraphLayoutResult,
    initial_nodes: list[GraphNode] | None = None,
    phase1_nodes: list[GraphNode] | None = None,
    base_name: str = "layout_comparison",
) -> str:
    """Plot graph snapshots, preferring Phase 1 vs Phase 2 for staged trials."""
    output_dir = os.path.join("test", "outputs", "graph_results")
    os.makedirs(output_dir, exist_ok=True)
    request_id, trial_id = get_tracking_ids()
    filename_parts = [part for part in (request_id, trial_id, base_name) if part]
    filename_parts.append(time.strftime("%Y%m%d-%H%M%S"))
    save_path = os.path.join(
        output_dir, f"{'_'.join(filename_parts)}.png"
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 11))

    if phase1_nodes is not None:
        _draw_on_axis(ax1, layout_result, phase1_nodes, "PHASE 1 (Uniform Radius)")
    elif initial_nodes is not None:
        _draw_on_axis(ax1, layout_result, initial_nodes, "INITIAL STATE (Pre-Physics)")
    else:
        ax1.text(
            0.5,
            0.5,
            "No Phase-1/Initial Data Provided",
            ha="center",
            transform=ax1.transAxes,
        )

    _draw_on_axis(
        ax2,
        layout_result,
        layout_result.nodes,
        f"PHASE 2 (Inflated Final) Score: {layout_result.score.total_score:.1f}",
    )

    fig.suptitle(
        f"Graph Layout Evolution | {layout_result.boundary.width}m x {layout_result.boundary.height}m",
        fontsize=18,
        fontweight="bold",
        y=0.95,
    )

    plt.tight_layout(rect=(0, 0.03, 1, 0.95))
    plt.savefig(save_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return save_path
