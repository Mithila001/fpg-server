import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import os
from datetime import datetime


def plot_refine_floor_plan(
    stage1_rooms=None, stage2_rooms=None, stage3_rooms=None, stage4_rooms=None
):
    """
    Plots provided refinement stages side-by-side.
    Skips any stage that is None or empty.
    """
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "outputs" / "refine"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Define all potential stages and their labels
    raw_stages = [stage1_rooms, stage2_rooms, stage3_rooms, stage4_rooms]
    raw_titles = [
        "Stage 1: Initial",
        "Stage 2: Refined",
        "Stage 3: Final",
        "Stage 4: Post-Final",
    ]

    # --- Filter out None or empty stages ---
    stages_data = []
    titles = []
    for data, title in zip(raw_stages, raw_titles):
        if data:  # Only add if the list is not None and not empty
            stages_data.append(data)
            titles.append(title)

    if not stages_data:
        print("No valid room data provided to plot.")
        return None

    # --- 1. Calculate Global Boundaries ---
    all_x = []
    all_y = []
    for rooms in stages_data:
        for room in rooms:
            all_x.extend([float(room["x"]), float(room["x_end"])])
            all_y.extend([float(room["y"]), float(room["y_end"])])

    padding = 5
    min_x, max_x = min(all_x) - padding, max(all_x) + padding
    min_y, max_y = min(all_y) - padding, max(all_y) + padding

    # --- 2. Dynamic Layout ---
    num_plots = len(stages_data)
    # Adjust width based on number of plots (8 inches per plot is usually a good ratio)
    fig, axes = plt.subplots(1, num_plots, figsize=(8 * num_plots, 10), squeeze=False)
    # squeeze=False ensures 'axes' is always a 2D array even if num_plots is 1
    axes = axes.flatten()

    colors = {
        "bedroom": "#AEC6CF",
        "bathroom": "#CFCFCF",
        "kitchen": "#FFB347",
        "attachedBathroom": "#BDBDBD",
        "veranda": "#77DD77",
        "garage": "#838996",
        "diningRoom": "#FDFD96",
        "livingRoom": "#FFB7CE",
        "hallway": "#E6E6FA",
        "verandaOutdoorSpace": "#C1E1C1",
    }

    for i, rooms in enumerate(stages_data):
        ax = axes[i]
        for room in rooms:
            x, y = float(room["x"]), float(room["y"])
            w = float(room["x_end"]) - x
            h = float(room["y_end"]) - y

            rect = patches.Rectangle(
                (x, y),
                w,
                h,
                linewidth=2,
                edgecolor="#333333",
                facecolor=colors.get(room["type"], "#FFFFFF"),
                alpha=0.8,
            )
            ax.add_patch(rect)

            room_name = str(room.get("name", "Unknown"))
            label = room_name.replace("_for_", "\n")
            ax.text(
                x + w / 2,
                y + h / 2,
                label,
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
                wrap=True,
            )

        ax.set_title(titles[i], fontsize=16, pad=20)
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_aspect("equal")
        ax.grid(True, linestyle=":", alpha=0.6)
        if i == 0:
            ax.set_ylabel("Y (Bottom-Up)")

    plt.tight_layout(pad=3.0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(output_dir, f"refine_{timestamp}.png")
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    # print(f"Refinement plot saved ({num_plots} stages): {save_path}")
    return save_path
