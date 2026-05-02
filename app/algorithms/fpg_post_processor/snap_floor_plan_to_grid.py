import os
from datetime import datetime
import matplotlib.pyplot as plt
from dataclasses import dataclass, replace
from typing import Tuple, Sequence

from app.algorithms.types.domain import ProcessedRoomData  # Import Sequence


def calculate_polygon_area(vertices: Sequence[Tuple[float, float]]) -> float:
    """
    Calculates area using Sequence to allow list[tuple[int, int]]
    to be passed in safely.
    """
    n = len(vertices)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        # Even if passed as ints, math operations will treat them as floats
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0


def plot_post_process(
    original: Sequence[ProcessedRoomData], snapped: Sequence[ProcessedRoomData]
):
    """
    Dedicated Plotter: Saves side-by-side comparison with a timestamped filename.
    """
    output_dir = "test/outputs/post_process/grid_snap"
    os.makedirs(output_dir, exist_ok=True)

    # Generate timestamp (e.g., 20260429_104530)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"grid_snap_comparison_{timestamp}.png"
    save_path = os.path.join(output_dir, filename)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    def render_plan(ax, plan: Sequence[ProcessedRoomData], title: str):
        for room in plan:
            if not room.vertices:
                continue

            # Extract coordinates
            x, y = zip(*room.vertices)

            # Plot boundary and fill
            ax.plot(x, y, linewidth=2, label=room.name)
            ax.fill(x, y, alpha=0.2)

            # Add room labels at the geometric center
            cx = sum(v[0] for v in room.vertices) / len(room.vertices)
            cy = sum(v[1] for v in room.vertices) / len(room.vertices)
            ax.text(cx, cy, room.name, fontsize=9, ha="center", fontweight="bold")

        ax.set_title(title, fontsize=14)
        ax.grid(True, which="both", linestyle=":", alpha=0.5)
        ax.set_aspect("equal")

    render_plan(ax1, original, "Original Floor Plan")
    render_plan(ax2, snapped, "Snapped (1x1 Grid)")

    plt.tight_layout()

    # Save with timestamped filename
    plt.savefig(save_path, dpi=200)
    plt.close(fig)

    # print(f"Plot successfully saved to: {save_path}")


def snap_floor_plan_to_grid(
    processed_floor_plan: list[ProcessedRoomData],
) -> list[ProcessedRoomData]:
    snapped_plan: list[ProcessedRoomData] = []

    for room in processed_floor_plan:
        # Explicitly casting to float in the tuple to match ProcessedRoomData.vertices
        snapped_vertices: list[Tuple[float, float]] = [
            (float(round(vx)), float(round(vy))) for vx, vy in room.vertices
        ]

        # calculate_polygon_area now accepts Sequence, so it won't complain
        new_area = calculate_polygon_area(snapped_vertices)

        snapped_room = replace(room, vertices=snapped_vertices, area=new_area)
        snapped_plan.append(snapped_room)

    plot_post_process(processed_floor_plan, snapped_plan)

    return snapped_plan
