from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.ticker as ticker
from datetime import datetime
from pathlib import Path


def plot_snap_vs_grid(
    original_solution: list[dict],
    snapped_solution: list[dict] | dict,
    output_dir: str | Path = "test/dev/gridSnap/",
) -> str:
    """Plot original and snapped room layouts side-by-side."""
    # Normalize snapped_solution shape
    if isinstance(snapped_solution, dict) and "rooms" in snapped_solution:
        snapped_rooms = snapped_solution["rooms"]
    else:
        snapped_rooms = snapped_solution

    # Validate
    if not isinstance(original_solution, list) or not isinstance(snapped_rooms, list):
        raise ValueError("original_solution and snapped_solution must be list-like")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%m%d%H-%M-%S")
    output_file = output_dir / f"grid_snap_compare_{timestamp}.png"

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))

    def _draw(ax, rooms, title, grid_size=8.0):
        if not rooms:
            ax.text(0.5, 0.5, "No rooms", ha="center", va="center")
            ax.set_axis_off()
            return

        min_x = min(room.get("x", 0) for room in rooms)
        min_y = min(room.get("y", 0) for room in rooms)
        max_x = max(room.get("x_end", room.get("x", 0) + room.get("w", 0)) for room in rooms)
        max_y = max(room.get("y_end", room.get("y", 0) + room.get("h", 0)) for room in rooms)

        # align grid boundaries to multiples
        plot_min_x = grid_size * (int(min_x // grid_size) - 1)
        plot_min_y = grid_size * (int(min_y // grid_size) - 1)
        plot_max_x = grid_size * (int(max_x // grid_size) + 2)
        plot_max_y = grid_size * (int(max_y // grid_size) + 2)

        ax.xaxis.set_major_locator(ticker.MultipleLocator(grid_size))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(grid_size))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1.0))
        ax.yaxis.set_minor_locator(ticker.MultipleLocator(1.0))

        ax.grid(True, which='minor', color='lightgray', linestyle='--', linewidth=0.3)
        ax.grid(True, which='major', color='gray', linestyle='-', linewidth=0.5)

        ax.tick_params(which='minor', length=2, labelsize=0)
        ax.tick_params(which='major', length=5, labelsize=8)

        for room in rooms:
            x = float(room.get("x", 0))
            y = float(room.get("y", 0))
            w = float(room.get("w", room.get("x_end", x) - x))
            h = float(room.get("h", room.get("y_end", y) - y))
            rect = patches.Rectangle((x, y), w, h, linewidth=1, edgecolor="blue", facecolor="none", zorder=3)
            ax.add_patch(rect)
            ax.text(x + w / 2, y + h / 2, room.get("name", ""), ha="center", va="center", fontsize=8, zorder=4)

        ax.set_title(title)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(plot_min_x, plot_max_x)
        ax.set_ylim(plot_min_y, plot_max_y)

    _draw(axes[0], original_solution, "Original Solution", grid_size=8.0)
    _draw(axes[1], snapped_rooms, "Snapped Solution", grid_size=8.0)

    fig.suptitle("Grid Snap Comparison")
    fig.savefig(output_file, dpi=150)
    plt.close(fig)

    return str(output_file)
