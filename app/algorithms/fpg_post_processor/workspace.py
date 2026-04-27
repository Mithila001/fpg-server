import os
import matplotlib.pyplot as plt
from shapely.geometry import box, MultiPolygon, Polygon, LineString
from shapely.ops import unary_union

# --- CONSTANTS & CONFIGURATION ---

ROOM_COLOR_MAP = {
    "bedroom": "#C1E1C1",  # Pastel Green
    "bathroom": "#AEC6CF",  # Pastel Blue
    "kitchen": "#FFB347",  # Pastel Orange
    "attachedBathroom": "#B39EB5",  # Pastel Purple
    "veranda": "#FDFD96",  # Pastel Yellow
    "garage": "#CFCFC4",  # Pastel Gray
    "diningRoom": "#FFD1DC",  # Pastel Pink
    "hallway": "#DEA5A4",  # Pastel Coral
    "verandaOutdoorSpace": "#E6E6FA",  # Lavender
    "livingRoom": "#87CEEB",  # Sky Blue
}

# The order in which rooms will attempt to expand into voids/recesses
ROOM_EXPAND_HIERARCHY = ["livingRoom", "kitchen", "hallway", "bedroom"]

# Granular configuration per room type
ROOM_EXPANSION_CONFIG = {
    "livingRoom": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": float("inf"),
        "MAX_ROOMS_TO_EXPAND": 1,
        "MAX_SELECTIONS": 2,
        "EXPANSION_PERCENTAGE": 0.50,  # Expands up to 50% of the wall length
    },
    "kitchen": {
        "MIN_WALL_LENGTH": 8,
        "MAX_WALL_LENGTH": 40,
        "MAX_ROOMS_TO_EXPAND": 1,
        "MAX_SELECTIONS": 1,
        "EXPANSION_PERCENTAGE": 0.40,
    },
    "hallway": {
        "MIN_WALL_LENGTH": 5,
        "MAX_WALL_LENGTH": float("inf"),
        "MAX_ROOMS_TO_EXPAND": 2,
        "MAX_SELECTIONS": 2,
        "EXPANSION_PERCENTAGE": 0.30,
    },
    "bedroom": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": 50,
        "MAX_ROOMS_TO_EXPAND": 2,
        "MAX_SELECTIONS": 1,
        "EXPANSION_PERCENTAGE": 0.50,
    },
}


def _get_spaces(polygons):
    """Helper to calculate the current union, voids, and recesses."""
    floor_union = unary_union(polygons)

    # 1. Identify Internal Voids
    internal_voids_list = []
    if isinstance(floor_union, Polygon):
        internal_voids_list = [Polygon(i) for i in floor_union.interiors]
    elif hasattr(floor_union, "geoms"):
        for poly in floor_union.geoms:
            internal_voids_list.extend([Polygon(i) for i in poly.interiors])
    internal_voids = MultiPolygon(internal_voids_list)

    # 2. Identify External Recesses
    convex_poly = floor_union.convex_hull
    all_holes = convex_poly.difference(floor_union)

    minx, miny, maxx, maxy = floor_union.bounds
    shrinked_bbox = box(minx + 10, miny + 10, maxx - 10, maxy - 10)

    external_recesses_list = []
    hole_geoms = getattr(all_holes, "geoms", [all_holes])
    for hole in hole_geoms:
        if hole and not hole.is_empty and hole.intersects(shrinked_bbox):
            external_recesses_list.append(hole)
    external_recesses = MultiPolygon(external_recesses_list)

    return floor_union, convex_poly, all_holes, internal_voids, external_recesses


def process_floor_plan(floor_plan_data, filename=None):
    # Initialize geometries map based on original floor plan data
    room_geoms = {
        i: box(room["x"], room["y"], room["x_end"], room["y_end"])
        for i, room in enumerate(floor_plan_data)
    }

    # Keep a snapshot of original state for the left-side Diagnostic Plot
    orig_union, orig_hull, orig_holes, orig_voids, orig_recesses = _get_spaces(
        list(room_geoms.values())
    )

    all_chosen_segments = []

    # --- HIERARCHICAL EXPANSION LOGIC ---
    for room_type in ROOM_EXPAND_HIERARCHY:
        if room_type not in ROOM_EXPANSION_CONFIG:
            continue

        config = ROOM_EXPANSION_CONFIG[room_type]

        # 1. Gather all rooms of this type
        eligible_rooms = [
            (i, r) for i, r in enumerate(floor_plan_data) if r["type"] == room_type
        ]

        # 2. Sort by current area (smallest first)
        eligible_rooms.sort(key=lambda item: room_geoms[item[0]].area)

        # 3. Trim to max allowed expanding rooms of this type
        rooms_to_process = eligible_rooms[: config["MAX_ROOMS_TO_EXPAND"]]

        for i, room in rooms_to_process:
            # Re-evaluate spaces BEFORE expanding this specific room,
            # so it "sees" the remaining empty spaces left by previous expansions
            _, _, _, internal_voids, external_recesses = _get_spaces(
                list(room_geoms.values())
            )

            current_poly = room_geoms[i]
            current_boundary = current_poly.boundary
            expandable_segments = []

            for space_type, geom in [
                ("internal", internal_voids),
                ("external", external_recesses),
            ]:
                if geom.is_empty:
                    continue

                inter = current_boundary.intersection(geom.buffer(0.2))
                lines = getattr(inter, "geoms", [inter])

                for line in lines:
                    if isinstance(line, LineString):
                        if (
                            config["MIN_WALL_LENGTH"]
                            <= line.length
                            <= config["MAX_WALL_LENGTH"]
                        ):
                            expandable_segments.append(
                                {
                                    "line": line,
                                    "type": space_type,
                                    "length": line.length,
                                    "target_geom": geom,
                                }
                            )

            # Prioritize Internal Voids over External, then by segment length (longest to shortest)
            expandable_segments.sort(
                key=lambda x: (0 if x["type"] == "internal" else 1, -x["length"])
            )

            # Pick max selections based on config
            chosen_segments = expandable_segments[: config["MAX_SELECTIONS"]]
            all_chosen_segments.extend(chosen_segments)

            # Generate expansion patches
            expanded_patches = []
            for seg in chosen_segments:
                max_dist = seg["length"] * config["EXPANSION_PERCENTAGE"]
                patch = (
                    seg["line"]
                    .buffer(max_dist, cap_style=2)
                    .intersection(seg["target_geom"])
                )
                expanded_patches.append(patch)

            # Update the specific room's geometry in our running dictionary
            if expanded_patches:
                room_geoms[i] = unary_union([current_poly] + expanded_patches)

    # --- PLOTTING ---
    if filename:
        _plot_side_by_side(
            floor_plan_data,
            orig_hull,
            orig_holes,
            orig_voids,
            orig_recesses,
            all_chosen_segments,
            room_geoms,  # Passing the full dictionary of updated rooms
            filename,
        )

    # Return the dictionary or list of updated polygons if needed by your parent caller
    # Here we convert it back to a list in the original order
    return [room_geoms[i] for i in range(len(floor_plan_data))]


def _plot_side_by_side(
    floor_plan_data,
    hull,
    all_holes,
    voids,
    recesses,
    chosen_segments,
    final_room_geoms,
    filename,
):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(
        os.path.join(current_dir, "../../../test/outputs/post_process/dev/")
    )
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    save_path = os.path.join(output_dir, filename)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(22, 11), facecolor="#FAFAFA")

    # --- Helper to handle Polygon/MultiPolygon plotting safely ---
    def plot_geom_fill(ax, geom, color, alpha, label="", hatch=None, edgecolor=None):
        if geom is None or geom.is_empty:
            return
        geoms = getattr(geom, "geoms", [geom])
        for i, p in enumerate(geoms):
            if isinstance(p, Polygon):
                ax.fill(
                    *p.exterior.xy,
                    color=color,
                    alpha=alpha,
                    label=label if i == 0 else "_nolegend_",
                    hatch=hatch,
                    edgecolor=edgecolor or color,
                )

    def plot_rooms(ax, geoms_dict, use_color_map=True):
        for i, room in enumerate(floor_plan_data):
            r_type = room["type"]
            color = (
                ROOM_COLOR_MAP.get(r_type, "#EEEEEE") if use_color_map else "#E0E7FF"
            )

            # Use updated geometry if available, otherwise fallback to original box
            if geoms_dict is not None and i in geoms_dict:
                geom = geoms_dict[i]
            else:
                geom = box(room["x"], room["y"], room["x_end"], room["y_end"])

            ax.fill(
                *geom.exterior.xy,
                color=color,
                alpha=0.8,
                edgecolor="#2D3748",
                linewidth=1.2,
            )

            c_x, c_y = geom.centroid.x, geom.centroid.y
            ax.text(
                c_x,
                c_y,
                room["name"],
                fontsize=7,
                fontweight="bold",
                ha="center",
                color="#2D3748",
            )

    # --- LEFT PLOT: DIAGNOSTIC (Neutral Rooms) ---
    ax1.set_title("STEP 1: EXPANSION ANALYSIS", fontsize=14, fontweight="bold", pad=15)

    if not hull.is_empty:
        ax1.plot(
            *hull.exterior.xy,
            color="#2E7D32",
            linestyle="--",
            linewidth=1.2,
            alpha=0.6,
            label="Convex Hull",
        )

    plot_geom_fill(ax1, all_holes, "#FF5252", 0.05, label="All Empty Spaces")
    plot_geom_fill(ax1, voids, "#E040FB", 0.3, label="Internal Voids", hatch="///")
    plot_geom_fill(
        ax1, recesses, "#FFD740", 0.3, label="External Recesses", hatch="\\\\\\"
    )

    plot_rooms(ax1, None, use_color_map=False)

    for i, seg in enumerate(chosen_segments):
        x, y = seg["line"].xy
        ax1.plot(
            x,
            y,
            color="#00E676",
            linewidth=6,
            solid_capstyle="round",
            label="Chosen Wall" if i == 0 else "_nolegend_",
        )

    # --- RIGHT PLOT: FINAL RESULT (Color Coded) ---
    ax2.set_title(
        "STEP 2: FINAL OPTIMIZED PLAN", fontsize=14, fontweight="bold", pad=15
    )
    plot_rooms(ax2, final_room_geoms, use_color_map=True)

    for ax in [ax1, ax2]:
        ax.set_aspect("equal")
        ax.axis("off")

    ax1.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.05),
        ncol=3,
        frameon=False,
        fontsize=10,
    )

    plt.suptitle(
        f"Floor Plan Optimization: {filename}", fontsize=18, y=0.98, fontweight="bold"
    )
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(save_path, dpi=200, facecolor=fig.get_facecolor())
    plt.close()
    print(f"Success: Analysis saved to {save_path}")
