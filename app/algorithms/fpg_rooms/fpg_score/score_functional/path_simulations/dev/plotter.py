from __future__ import annotations
from typing import Any, Dict, List, Mapping

# Move imports to the top level
import matplotlib
matplotlib.use("Agg")  # Must be called before pyplot
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np



def _plot_floorplan_context(ax, room_polys_by_type: Dict[str, List[Any]], show_labels: bool = True):
    """Draws the outlines and labels of rooms to provide context for the simulation."""
    for room_type, polys in room_polys_by_type.items():
        for poly in polys:
            if poly.is_empty:
                continue
            # Draw the room fill (very light)
            x, y = poly.exterior.xy
            ax.fill(x, y, alpha=0.05, fc="black", ec="none")
            # Draw the room boundaries (the "walls")
            ax.plot(x, y, color="#455a64", linewidth=0.8, alpha=0.6)
            
            # Add room labels at the center
            if show_labels:
                centroid = poly.centroid
                ax.text(
                    centroid.x, centroid.y, 
                    room_type.replace("_", " ").title(),
                    fontsize=7, ha='center', va='center', 
                    alpha=0.5, fontweight='bold', color="#37474f"
                )


def save_path_simulation_plot(
    *,
    output_path: str,
    walkable: Any,
    room_polys_by_type: Dict[str, List[Any]],
    paths: List[Dict[str, Any]],
    grid: Any,
    traffic: List[List[int]],
    hallway_mask: List[List[bool]],
) -> None:

    # Set a clean, modern style
    fig, axes = plt.subplots(1, 3, figsize=(22, 7), dpi=150, facecolor='#f8f9fa')
    ax_paths, ax_hallway, ax_heat = axes

    # --- 1. SIMULATED PATHS ---
    ax_paths.set_title("Circulation Routes", fontsize=14, pad=15, fontweight='bold')
    _plot_floorplan_context(ax_paths, room_polys_by_type)
    
    colors = {
        "entry_to_kitchen": "#E65100",   # Deep Orange
        "entry_to_bedroom": "#0D47A1",   # Blue
        "entry_to_bathroom": "#7B1FA2",  # Purple
        "bedroom_to_bathroom": "#2E7D32",# Green
        "bedroom_to_kitchen": "#C62828", # Red
    }
    
    legend_handles = []
    seen_kinds = set()
    
    for path in paths:
        kind = path["kind"]
        polyline = path["polyline"]
        if not polyline: continue
        
        xs, ys = zip(*polyline)
        line, = ax_paths.plot(xs, ys, color=colors.get(kind, "#424242"), linewidth=2.5, alpha=0.8, zorder=3)
        
        if kind not in seen_kinds:
            legend_handles.append(mpatches.Patch(color=colors.get(kind, "#424242"), label=kind.replace("_", " ").title()))
            seen_kinds.add(kind)

    ax_paths.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=8)

    # --- 2. UNUSED HALLWAY (EFFICIENCY) ---
    ax_hallway.set_title("Hallway Dead Zones", fontsize=14, pad=15, fontweight='bold')
    _plot_floorplan_context(ax_hallway, room_polys_by_type)
    
    # Highlight hallway specifically
    hallway_polys = room_polys_by_type.get("hallway", [])
    for poly in hallway_polys:
        x, y = poly.exterior.xy
        ax_hallway.fill(x, y, fc="#fff176", alpha=0.3, label="Hallway Area")

    # Mark cells in hallways that never saw traffic
    dead_xs, dead_ys = [], []
    for y_idx in range(len(grid.ys)):
        for x_idx in range(len(grid.xs)):
            if hallway_mask[y_idx][x_idx] and traffic[y_idx][x_idx] == 0:
                dead_xs.append(grid.xs[x_idx])
                dead_ys.append(grid.ys[y_idx])
    
    if dead_xs:
        ax_hallway.scatter(dead_xs, dead_ys, s=12, c="#d32f2f", marker='x', alpha=0.7, label="Unused Space")

    # --- 3. TRAFFIC INTENSITY (HEATMAP) ---
    ax_heat.set_title("Traffic Intensity", fontsize=14, pad=15, fontweight='bold')
    
    # Use a high-quality 'magma' or 'inferno' map for heat
    # We overlay the floorplan ON TOP of the heat for better visibility
    extent = [min(grid.xs), max(grid.xs), min(grid.ys), max(grid.ys)]
    
    # Smooth out the traffic grid using bilinear interpolation
    im = ax_heat.imshow(
        traffic, 
        origin="lower", 
        extent=extent, 
        cmap="magma", 
        interpolation="bilinear", # This makes it look like a real heatmap
        aspect="equal"
    )
    
    # Overlay the floorplan lines in white/light grey for contrast against the dark heat map
    for _, polys in room_polys_by_type.items():
        for poly in polys:
            x, y = poly.exterior.xy
            ax_heat.plot(x, y, color="white", linewidth=1, alpha=0.4)

    plt.colorbar(im, ax=ax_heat, fraction=0.046, pad=0.04).set_label('Path Frequency', fontsize=10)

    # Standardize all axes
    for ax in axes:
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off") # Remove the outer box/ticks for a cleaner look

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close(fig)