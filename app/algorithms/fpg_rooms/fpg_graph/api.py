from __future__ import annotations

from typing import Any

from app.algorithms.fpg_rooms.types.room import FpgRequirements

from .adapters import build_boundary, build_edges, build_nodes, initialize_positions
from .physics.engine import run_force_directed_layout
from .score.scorer import score_graph_layout
from .types import GraphBoundary, GraphLayoutResult, GraphNode, GraphPhysicsConfig

import os
import time
import matplotlib.pyplot as plt
import matplotlib.patches as patches

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
    initialize_positions(nodes, boundary, seed=seed, explicit_positions=explicit_positions)

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
    if score.total_score > 75:
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
    requested_padding: float = 10.0
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
def plot_graph_layout(layout_result: GraphLayoutResult, base_name: str = "layout"):
    """
    Plots high-fidelity graph layout with original vs. padded boundary comparison.
    """
    # 1. Capture original boundary for plotting limits
    orig_b = layout_result.boundary
    nodes = layout_result.nodes
    requested_padding = 10.0

    # 2. Calculate the Shrunk/Padded Box bounds WITHOUT mutating nodes yet
    # Find raw tight extents
    tight_min_x = min(node.x - node.radius for node in nodes)
    tight_max_x = max(node.x + node.radius for node in nodes)
    tight_min_y = min(node.y - node.radius for node in nodes)
    tight_max_y = max(node.y + node.radius for node in nodes)

    # Calculate allowable padding based on original boundary constraints
    pad_l = max(0, min(requested_padding, tight_min_x))
    pad_r = max(0, min(requested_padding, orig_b.width - tight_max_x))
    pad_b = max(0, min(requested_padding, tight_min_y))
    pad_t = max(0, min(requested_padding, orig_b.height - tight_max_y))

    # The actual box coordinates to draw in the plot
    shrunk_x = tight_min_x - pad_l
    shrunk_y = tight_min_y - pad_b
    shrunk_w = (tight_max_x - tight_min_x) + pad_l + pad_r
    shrunk_h = (tight_max_y - tight_min_y) + pad_b + pad_t

    # 3. Setup Plotting
    output_dir = os.path.join("test", "outputs", "graph_results")
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"{base_name}_{time.strftime('%Y%m%d-%H%M%S')}.png")

    fig, ax = plt.subplots(figsize=(12, 10))

    # Styling Palette
    colors = {
        "hallway": "#95a5a6", "kitchen": "#f1c40f", "livingRoom": "#3498db",
        "diningRoom": "#e67e22", "bedroom": "#a29bfe", "garage": "#2d3436",
        "veranda": "#26de81", "bathroom": "#81ecec",
    }
    default_color = "#dfe6e9"

    # 4. Draw Original Boundary (Reference)
    ax.add_patch(patches.Rectangle(
        (0, 0), orig_b.width, orig_b.height,
        linewidth=1, edgecolor="#b2bec3", facecolor="#f8f9fa", 
        linestyle='-', alpha=0.5, zorder=0, label="Original Boundary"
    ))

    # 5. Draw Padded Shrunk Boundary (Red Dotted Line)
    ax.add_patch(patches.Rectangle(
        (shrunk_x, shrunk_y), shrunk_w, shrunk_h,
        linewidth=2, edgecolor='red', facecolor='none',
        linestyle='--', zorder=5, label=f"Padded Boundary (+{max(pad_l, pad_r)}m)"
    ))

    # 6. Draw Edges (High Quality)
    node_map = {node.id: node for node in nodes}
    for edge in layout_result.edges:
        source, target = node_map.get(edge.source_id), node_map.get(edge.target_id)
        if source and target:
            linewidth = 1.0 + (edge.weight * 2)
            ax.plot(
                [source.x, target.x], [source.y, target.y],
                color="#b2bec3", linewidth=linewidth,
                alpha=0.4, zorder=1
            )

    # 7. Draw Nodes (High Quality)
    for node in nodes:
        face_color = colors.get(node.room_type, default_color)
        edge_style = '--' if getattr(node, 'synthesized', False) else '-'
        
        ax.add_patch(patches.Circle(
            (node.x, node.y), node.radius,
            linewidth=1.5, edgecolor="#2d3436", facecolor=face_color,
            linestyle=edge_style, alpha=0.9, zorder=3
        ))
        
        display_name = getattr(node, 'name', node.id)
        ax.text(
            node.x, node.y, display_name,
            fontsize=8, ha='center', va='center', fontweight='bold',
            color='black' if face_color != "#2d3436" else 'white', zorder=4
        )

    # 8. Final Formatting
    ax.set_xlim(-2, orig_b.width + 2)
    ax.set_ylim(-2, orig_b.height + 2)
    ax.set_aspect('equal')
    
    res = layout_result.score
    utilization = (shrunk_w * shrunk_h) / (orig_b.width * orig_b.height) * 100
    title_str = (
        f"Score: {res.total_score:.1f} | Area Utilized: {utilization:.1f}%\n"
        f"Original: {orig_b.width}x{orig_b.height} | Padded Shrunk: {shrunk_w:.1f}x{shrunk_h:.1f}"
    )
    ax.set_title(title_str, loc='left', fontsize=10, pad=10)
    
    plt.grid(True, linestyle=':', alpha=0.3)
    plt.legend(loc='upper right', fontsize='small')
    plt.xlabel("Width (m)")
    plt.ylabel("Height (m)")
    
    plt.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close(fig)

    print(f"✅ Unique layout saved to: {save_path}")
    return save_path