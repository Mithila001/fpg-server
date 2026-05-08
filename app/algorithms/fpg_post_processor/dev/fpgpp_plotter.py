import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon


def plot_floorplan_comparison(before_data, after_data):
    """
    Plots floorplans and saves to test\outputs\post_process\dev with timestamped filename.
    """
    # 1. Setup the directory path
    output_dir = os.path.join("test", "outputs", "post_process", "dev")
    os.makedirs(output_dir, exist_ok=True)  # Creates folders if they don't exist

    # 2. Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"fpgpp_hallway_{timestamp}.png"
    save_path = os.path.join(output_dir, filename)

    # 3. Setup Plotting (Server-level/No UI)
    color_map = {
        "bedroom": "#ff9999",
        "bathroom": "#66b3ff",
        "kitchen": "#99ff99",
        "attachedBathroom": "#ffcc99",
        "veranda": "#c2c2f0",
        "garage": "#ffb3e6",
        "diningRoom": "#c4fb6d",
        "livingRoom": "#fdbb84",
        "hallway": "#d9d9d9",
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    def draw_layout(ax, rooms, title):
        ax.set_title(title, fontsize=14, fontweight="bold")
        all_points = []
        for room in rooms:
            if not room.vertices:
                continue
            poly = Polygon(
                room.vertices,
                closed=True,
                facecolor=color_map.get(room.type, "#eeeeee"),
                edgecolor="black",
                alpha=0.8,
                label=room.type,
            )
            ax.add_patch(poly)
            xs, ys = zip(*room.vertices)
            ax.text(
                sum(xs) / len(xs),
                sum(ys) / len(ys),
                room.name,
                fontsize=7,
                ha="center",
                fontweight="black",
            )
            all_points.extend(room.vertices)

        ax.set_aspect("equal")
        if all_points:
            xs, ys = zip(*all_points)
            ax.set_xlim(min(xs) - 10, max(xs) + 10)
            ax.set_ylim(min(ys) - 10, max(ys) + 10)
        ax.invert_yaxis()
        ax.grid(True, linestyle=":", alpha=0.5)

    draw_layout(ax1, before_data, "Before (Snapped)")
    draw_layout(ax2, after_data, "After (Union)")

    # Deduplicate legend labels
    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    fig.legend(by_label.values(), by_label.keys(), loc="lower center", ncol=5)

    # 4. Save and Close
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])  # type: ignore
    plt.savefig(save_path, dpi=150)
    plt.close(fig)

    print(f"Successfully saved floorplan to: {save_path}")


# Call the function
# plot_floorplan_comparison(snapped_results, union_hallways_fp)
