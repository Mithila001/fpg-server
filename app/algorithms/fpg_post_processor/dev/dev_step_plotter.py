import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from shapely.geometry import Polygon


ROOM_COLOR_MAP = {
    "bedroom": "#C1E1C1",
    "bathroom": "#AEC6CF",
    "kitchen": "#FFB347",
    "attachedBathroom": "#B39EB5",
    "veranda": "#FDFD96",
    "garage": "#CFCFC4",
    "diningRoom": "#FFD1DC",
    "hallway": "#DEA5A4",
    "verandaOutdoorSpace": "#E6E6FA",
    "livingRoom": "#87CEEB",
}


def plot_step_progression(floor_plan_data, hierarchy_snapshots, filename="floor_plan_analysis.png"):
    if not hierarchy_snapshots:
        return

    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(
        os.path.join(current_dir, "../../../../test/outputs/post_process/dev_step_plotter/")
    )
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, filename)

    panel_count = len(hierarchy_snapshots)
    fig_width = max(6.0 * panel_count, 8.0)
    fig, axes = plt.subplots(1, panel_count, figsize=(fig_width, 7.5), facecolor="#FAFAFA")
    if panel_count == 1:
        axes = [axes]

    x_min, x_max, y_min, y_max = _get_plot_bounds(floor_plan_data)

    for axis, snapshot in zip(axes, hierarchy_snapshots):
        _plot_step_panel(axis, floor_plan_data, snapshot)
        axis.set_xlim(x_min, x_max)
        axis.set_ylim(y_min, y_max)
        axis.set_aspect("equal")
        
        # --- Grid Configuration ---
        # Ensure ticks are visible to show the grid, but hide labels if you want a clean look
        axis.xaxis.set_major_locator(ticker.MultipleLocator(2.0))
        axis.yaxis.set_major_locator(ticker.MultipleLocator(2.0))
        axis.grid(True, which='major', color="#545454", linestyle='--', linewidth=0.5, alpha=0.5)
        # Hide the numeric tick labels to keep the "off" aesthetic while keeping the grid
        axis.set_xticklabels([])
        axis.set_yticklabels([])
        # Remove the outer frame spines but keep the grid
        for spine in axis.spines.values():
            spine.set_visible(False)

    plt.suptitle(
        f"Hierarchy Expansion Steps: {filename}",
        fontsize=18,
        y=0.98,
        fontweight="bold",
    )
    plt.tight_layout(rect=[0, 0.02, 1, 0.94])
    plt.savefig(save_path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Step progression plot saved: {save_path}")


def _plot_step_panel(axis, floor_plan_data, snapshot):
    step_name = snapshot.get("step_name", "step")
    chosen_segments = snapshot.get("chosen_segments", [])
    room_geoms = snapshot.get("room_geoms", {})

    axis.set_title(step_name, fontsize=13, fontweight="bold", pad=12)

    for index, room in enumerate(floor_plan_data):
        geom = room_geoms.get(index)
        if geom is None or geom.is_empty:
            continue

        color = ROOM_COLOR_MAP.get(room["type"], "#E0E7FF")
        _fill_geom(axis, geom, color=color, alpha=0.8)

        center_x, center_y = geom.centroid.x, geom.centroid.y
        axis.text(
            center_x,
            center_y,
            room["name"],
            fontsize=7,
            fontweight="bold",
            ha="center",
            color="#2D3748",
            zorder=5  # Ensure text is above grid
        )

    for segment_index, segment in enumerate(chosen_segments):
        x_coords, y_coords = segment["line"].xy
        axis.plot(
            x_coords,
            y_coords,
            color="#00C853",
            linewidth=6,
            solid_capstyle="round",
            alpha=0.95,
            zorder=10 # Ensure lines are above grid
        )
        if segment_index == 0:
            midpoint = segment["line"].interpolate(0.5, normalized=True)
            axis.text(
                midpoint.x,
                midpoint.y,
                "chosen",
                fontsize=7,
                fontweight="bold",
                color="#1B5E20",
                ha="center",
                va="bottom",
                zorder=11
            )

    axis.text(
        0.02,
        0.98,
        f"Chosen walls: {len(chosen_segments)}",
        transform=axis.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="left",
        va="top",
        bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
        zorder=12
    )


def _fill_geom(axis, geom, color, alpha):
    geoms = getattr(geom, "geoms", [geom])
    for polygon in geoms:
        if isinstance(polygon, Polygon):
            axis.fill(
                *polygon.exterior.xy,
                color=color,
                alpha=alpha,
                edgecolor="#2D3748",
                linewidth=1.1,
                zorder=2 # Ensure rooms are above grid
            )


def _get_plot_bounds(floor_plan_data):
    min_x = min(room["x"] for room in floor_plan_data)
    min_y = min(room["y"] for room in floor_plan_data)
    max_x = max(room["x_end"] for room in floor_plan_data)
    max_y = max(room["y_end"] for room in floor_plan_data)
    padding_x = max((max_x - min_x) * 0.05, 5)
    padding_y = max((max_y - min_y) * 0.05, 5)
    return (
        min_x - padding_x,
        max_x + padding_x,
        min_y - padding_y,
        max_y + padding_y,
    )