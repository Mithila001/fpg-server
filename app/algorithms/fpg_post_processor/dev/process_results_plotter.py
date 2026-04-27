import os
from datetime import datetime
import matplotlib

# Force "Agg" backend for headless server execution
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.ticker as ticker


def save_floor_plan_plots(floor_data, output_dir=r"test\outputs\post_process"):
    """
    Renders floor plans to a file with Y-axis flipped (bottom at top),
    room types as labels, and a 10x10 unit grid.
    """
    if (
        isinstance(floor_data, list)
        and len(floor_data) > 0
        and isinstance(floor_data[0], dict)
    ):
        floor_plans = [floor_data]
    else:
        floor_plans = floor_data

    num_plans = len(floor_plans)
    fig, axes = plt.subplots(1, num_plans, figsize=(12 * num_plans, 10), squeeze=False)

    color_map = {
        "bedroom": "#AED6F1",
        "bathroom": "#85C1E9",
        "attachedBathroom": "#5DADE2",
        "kitchen": "#ABEBC6",
        "diningRoom": "#F9E79F",
        "livingRoom": "#FAD7A0",
        "garage": "#EBEDEF",
        "hallway": "#D7BDE2",
        "veranda": "#D5F5E3",
        "verandaOutdoorSpace": "#F5B7B1",
    }

    for idx, plan in enumerate(floor_plans):
        ax = axes[0, idx]
        max_x, max_y = 0, 0

        for room in plan:
            x, y, w, h = room["x"], room["y"], room["w"], room["h"]
            rtype = room.get("type", "room")

            # Create rectangle
            rect = patches.Rectangle(
                (x, y),
                w,
                h,
                linewidth=2,
                edgecolor="#34495E",
                facecolor=color_map.get(rtype, "#BDC3C7"),
                alpha=0.8,
            )
            ax.add_patch(rect)

            # Label using room TYPE
            ax.text(
                x + w / 2,
                y + h / 2,
                rtype,
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                wrap=True,
            )

            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)

        ax.set_title(f"Floor Layout {idx + 1}", fontsize=14, pad=20)

        # Setting limits
        ax.set_xlim(-5, max_x + 10)
        ax.set_ylim(-5, max_y + 10)

        # Grid Configuration: 10 by 10 units
        ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(10))
        ax.grid(True, which="major", linestyle="-", color="#CCCCCC", alpha=0.5)

        ax.set_aspect("equal")
        # ax.invert_yaxis() is REMOVED so that bottom (higher Y) is at the top of the plot area

    # File Handling
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"plan_{timestamp}.png"
    save_path = os.path.join(output_dir, filename)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close(fig)

    return save_path
