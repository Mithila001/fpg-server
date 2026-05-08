import os
import matplotlib.pyplot as plt


def plot_and_save_results(
    floor_plan_data,
    floor_union,
    convex_poly,
    holes,
    candidate_pockets,
    filename="floor_plan_analysis.png",
):
    # Target path setup
    current_dir = os.path.dirname(__file__)
    output_dir = os.path.abspath(
        os.path.join(current_dir, "../../../../test/outputs/post_process/dev/")
    )

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    save_path = os.path.join(output_dir, filename)

    fig, ax = plt.subplots(figsize=(12, 10))

    # Helper to plot geometries
    def plot_geom_collection(geom, color, alpha, label, hatch=None):
        if geom is None or geom.is_empty:
            return

        # Ensure we are working with a list of geometries (Polygon or MultiPolygon)
        # Using getattr with a default avoids the Pylance/Linter warning
        geoms = getattr(geom, "geoms", [geom])

        for i, p in enumerate(geoms):
            # Map coordinates
            x, y = p.exterior.xy
            ax.fill(
                x,
                y,
                color=color,
                alpha=alpha,
                label=label if i == 0 else "_nolegend_",
                hatch=hatch,  # Pass directly, not via extra_args
            )

    # 1. Draw Convex Hull (Bottom Layer)
    if not convex_poly.is_empty:
        ax.plot(
            *convex_poly.exterior.xy,
            color="forestgreen",
            linestyle="--",
            linewidth=1,
            label="Convex Hull",
        )
        ax.fill(*convex_poly.exterior.xy, color="green", alpha=0.03)

    # 2. Draw ALL Identified Holes (Light Red)
    plot_geom_collection(holes, "red", 0.15, "External/Deep Holes")

    # 3. Draw Candidate Pockets (Highlighted in Orange/Gold)
    plot_geom_collection(candidate_pockets, "gold", 0.6, "Fix Candidate Pockets")

    # 4. Draw the Floor Union (The "Mass" of the house)
    plot_geom_collection(floor_union, "royalblue", 0.4, "Building Footprint")

    # 5. Draw Individual Room Outlines
    for room in floor_plan_data:
        rect_x = [room["x"], room["x_end"], room["x_end"], room["x"], room["x"]]
        rect_y = [room["y"], room["y"], room["y_end"], room["y_end"], room["y"]]
        ax.plot(rect_x, rect_y, color="black", linewidth=0.8, alpha=0.5)

        center_x = room["x"] + (room.get("w", 0) / 2)
        center_y = room["y"] + (room.get("h", 0) / 2)
        ax.text(center_x, center_y, room["name"], fontsize=7, ha="center", alpha=0.6)

    # 6. Draw the Shrunk Bounding Box for reference
    _plot_shrunk_bounding_box(ax, floor_union, shrink_amount=10)

    # Formatting
    ax.set_aspect("equal")
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(
        by_label.values(), by_label.keys(), loc="upper left", bbox_to_anchor=(1, 1)
    )

    plt.title(f"Floor Plan Analysis: {filename}", pad=20)
    plt.grid(True, linestyle=":", alpha=0.3)
    plt.tight_layout()

    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Detailed plot saved: {save_path}")


def _plot_shrunk_bounding_box(ax, floor_union, shrink_amount=10):
    if floor_union.is_empty:
        return
    minx, miny, maxx, maxy = floor_union.bounds
    s_minx, s_miny, s_maxx, s_maxy = (
        minx + shrink_amount,
        miny + shrink_amount,
        maxx - shrink_amount,
        maxy - shrink_amount,
    )

    if s_maxx > s_minx and s_maxy > s_miny:
        rect_x = [s_minx, s_maxx, s_maxx, s_minx, s_minx]
        rect_y = [s_miny, s_miny, s_maxy, s_maxy, s_miny]
        ax.plot(
            rect_x,
            rect_y,
            color="darkorange",
            linestyle="--",
            linewidth=1.5,
            label="Shrink Zone",
        )
