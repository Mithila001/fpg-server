import os
import matplotlib.pyplot as plt
from shapely import envelope
from shapely.geometry import box, MultiPolygon, Polygon, LineString
from shapely.ops import unary_union, substring

from app.algorithms.fpg_post_processor.dev.dev_step_plotter import (
    plot_step_progression,
)

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

ROOM_EXPAND_HIERARCHY = ["livingRoom", "kitchen", "hallway", "bedroom"]

ROOM_EXPANSION_CONFIG = {
    "livingRoom": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": 30,
        "MAX_ROOMS_TO_EXPAND": 1,
        "MAX_SELECTIONS": 2,
        "EXPANSION_PERCENTAGE": 0.50,
        "EXPANSION_MAX_DISTANCE": 20,
    },
    "kitchen": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": 30,
        "MAX_ROOMS_TO_EXPAND": 1,
        "MAX_SELECTIONS": 1,
        "EXPANSION_PERCENTAGE": 0.40,
        "EXPANSION_MAX_DISTANCE": 10,
    },
    "hallway": {
        "MIN_WALL_LENGTH": 5,
        "MAX_WALL_LENGTH": 40,
        "MAX_ROOMS_TO_EXPAND": 3,
        "MAX_SELECTIONS": 3,
        "EXPANSION_PERCENTAGE": 0.50,
        "EXPANSION_MAX_DISTANCE": 10,
    },
    "bedroom": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": 40,
        "MAX_ROOMS_TO_EXPAND": 3,
        "MAX_SELECTIONS": 1,
        "EXPANSION_PERCENTAGE": 0.50,
        "EXPANSION_MAX_DISTANCE": 10,
    },
}


def _get_spaces(polygons):
    """Helper to calculate current union, voids, and orthogonal recesses."""
    floor_union = unary_union(polygons)

    # 1. Identify Internal Voids (Holes inside the building)
    internal_voids_list = []
    if isinstance(floor_union, Polygon):
        internal_voids_list = [Polygon(i) for i in floor_union.interiors]
    elif hasattr(floor_union, "geoms"):
        for poly in floor_union.geoms:
            internal_voids_list.extend([Polygon(i) for i in poly.interiors])
    internal_voids = MultiPolygon(internal_voids_list)

    # 2. Identify External Recesses (Option B: Orthogonal Constraint)
    # We use .envelope instead of .convex_hull to ensure axis-aligned (square) boundaries
    orthogonal_envelope = floor_union.envelope
    all_holes = orthogonal_envelope.difference(floor_union)

    # Define a shrinked area to filter out tiny perimeter gaps
    minx, miny, maxx, maxy = floor_union.bounds
    shrinked_bbox = box(minx + 10, miny + 10, maxx - 10, maxy - 10)

    external_recesses_list = []
    hole_geoms = getattr(all_holes, "geoms", [all_holes])
    for hole in hole_geoms:
        # Only consider gaps that are somewhat "internal" to the footprint
        if hole and not hole.is_empty and hole.intersects(shrinked_bbox):
            external_recesses_list.append(hole)
    external_recesses = MultiPolygon(external_recesses_list)

    return (
        floor_union,
        orthogonal_envelope,
        all_holes,
        internal_voids,
        external_recesses,
    )


def process_floor_plan(floor_plan_data, filename=None):
    room_geoms = {
        i: box(room["x"], room["y"], room["x_end"], room["y_end"])
        for i, room in enumerate(floor_plan_data)
    }

    all_chosen_segments = []
    hierarchy_snapshots = []

    print("\n" + "=" * 50)
    print("STARTING HIERARCHY EXPANSION PROCESS")
    print("=" * 50)

    for room_type in ROOM_EXPAND_HIERARCHY:
        if room_type not in ROOM_EXPANSION_CONFIG:
            continue

        config = ROOM_EXPANSION_CONFIG[room_type]
        eligible_rooms = [
            (i, r) for i, r in enumerate(floor_plan_data) if r["type"] == room_type
        ]
        eligible_rooms.sort(key=lambda item: room_geoms[item[0]].area)
        rooms_to_process = eligible_rooms[: config["MAX_ROOMS_TO_EXPAND"]]

        print(f"\n--- Checking Room Type: {room_type.upper()} ---")

        # Track chosen segments for this specific hierarchy step snapshot
        step_chosen_segments = []

        for i, room in rooms_to_process:
            # We call _get_spaces here to get the current state of the floor
            _, _, _, internal_voids, external_recesses = _get_spaces(
                list(room_geoms.values())
            )

            current_poly = room_geoms[i]
            current_boundary = current_poly.boundary
            expandable_segments = []

            print(f" Processing Room #{i} ({room_type})")

            for space_type, geom in [
                ("internal", internal_voids),
                ("external", external_recesses),
            ]:
                if geom.is_empty:
                    continue

                inter = current_boundary.intersection(geom.buffer(0.2))
                lines = getattr(inter, "geoms", [inter])

                for line_idx, line in enumerate(lines):
                    if isinstance(line, LineString):
                        original_length = line.length
                        work_line = line

                        is_truncated = False
                        if original_length > config["MAX_WALL_LENGTH"]:
                            work_line = substring(line, 0, config["MAX_WALL_LENGTH"])
                            is_truncated = True

                        current_length = work_line.length
                        is_valid = current_length >= config["MIN_WALL_LENGTH"]

                        if is_valid:
                            expandable_segments.append(
                                {
                                    "line": work_line,
                                    "type": space_type,
                                    "length": current_length,
                                    "target_geom": geom,
                                }
                            )

            expandable_segments.sort(
                key=lambda x: (0 if x["type"] == "internal" else 1, -x["length"])
            )
            chosen_segments = expandable_segments[: config["MAX_SELECTIONS"]]

            if chosen_segments:
                all_chosen_segments.extend(chosen_segments)
                step_chosen_segments.extend(chosen_segments)
                expanded_patches = []
                for seg in chosen_segments:
                    calculated_dist = seg["length"] * config["EXPANSION_PERCENTAGE"]
                    max_dist = min(calculated_dist, config["EXPANSION_MAX_DISTANCE"])

                    patch = (
                        seg["line"]
                        .buffer(max_dist, cap_style=2)
                        .intersection(seg["target_geom"])
                    )
                    expanded_patches.append(patch)

                room_geoms[i] = unary_union([current_poly] + expanded_patches)

        # Snapshot for the step plotter
        hierarchy_snapshots.append(
            {
                "step_name": room_type,
                "room_geoms": room_geoms.copy(),
                "chosen_segments": step_chosen_segments,
            }
        )

    # --- FIX: Calculate final spaces for the side-by-side plot ---
    (
        floor_union,
        orthogonal_envelope,
        all_holes,
        final_internal_voids,
        final_external_recesses,
    ) = _get_spaces(list(room_geoms.values()))

    print("\n" + "=" * 50)
    print("EXPANSION PROCESS COMPLETE")
    print("=" * 50 + "\n")

    if filename:
        # 1. Step Progression Plot (Requires its own internal logic)
        plot_step_progression(floor_plan_data, hierarchy_snapshots, filename=filename)

        # 2. Final Side-by-Side Analysis Plot
        _plot_side_by_side(
            floor_plan_data,
            orthogonal_envelope,
            all_holes,
            final_internal_voids,
            final_external_recesses,
            all_chosen_segments,  # Pass the accumulated list
            room_geoms,
            filename,
        )

    return [room_geoms[i] for i in range(len(floor_plan_data))]


## Plotter Function Below


def _plot_side_by_side(
    floor_plan_data,
    envelope,
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

    # --- LEFT PLOT: DIAGNOSTIC ---
    ax1.set_title(
        "STEP 1: EXPANSION ANALYSIS (ORTHOGONAL)",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )

    if not envelope.is_empty:
        ax1.plot(
            *envelope.exterior.xy,
            color="#2E7D32",
            linestyle="--",
            linewidth=1.2,
            alpha=0.6,
            label="Bounding Envelope",
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

    # --- RIGHT PLOT: FINAL RESULT ---
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
