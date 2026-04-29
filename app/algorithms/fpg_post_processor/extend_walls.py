import os
from typing import List, Tuple, TypedDict
import matplotlib.pyplot as plt
from shapely.affinity import translate
from shapely.geometry import box, MultiPolygon, Polygon, LineString
from shapely.ops import unary_union, substring
from app.algorithms.types.domain import ProcessedRoomData

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

ROOM_EXPAND_HIERARCHY = ["livingRoom", "veranda", "kitchen", "hallway", "bedroom"]

ROOM_EXPANSION_CONFIG = {
    "livingRoom": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": 40,
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
    "veranda": {
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


def _extrude_wall_patch(line, target_geom, max_distance, debug_label):
    print(f"\n  [EXTRUDE-START] Processing: {debug_label}")

    if line.is_empty or target_geom.is_empty:
        print(f"  [EXTRUDE-SKIP] Empty geometry detected for {debug_label}.")
        return None

    coords = list(line.coords)
    if len(coords) < 2:
        print(
            f"  [EXTRUDE-SKIP] Line has insufficient points ({len(coords)}) for {debug_label}."
        )
        return None

    x1, y1 = coords[0]
    x2, y2 = coords[-1]
    dx = x2 - x1
    dy = y2 - y1
    print(
        f"  [DEBUG] Line length: {line.length:.2f} | Vector: dx={dx:.2f}, dy={dy:.2f}"
    )

    if abs(dx) >= abs(dy):
        normals = [(0.0, 1.0), (0.0, -1.0)]
        print(f"  [DEBUG] Axis: Horizontal-ish. Testing Y-normals.")
    else:
        normals = [(1.0, 0.0), (-1.0, 0.0)]
        print(f"  [DEBUG] Axis: Vertical-ish. Testing X-normals.")

    mid = line.interpolate(0.5, normalized=True)
    chosen_normal = None

    # Phase 1: Direct containment probe
    for nx, ny in normals:
        probe = translate(mid, xoff=nx * 0.5, yoff=ny * 0.5)
        if target_geom.contains(probe):
            chosen_normal = (nx, ny)
            print(f"  [DECISION] Normal {chosen_normal} chosen via Containment Probe.")
            break

    # Phase 2: Intersection scoring (if Phase 1 fails)
    if chosen_normal is None:
        print(f"  [DEBUG] Containment probe failed. Trying intersection scoring...")
        best_score = 0.0
        for nx, ny in normals:
            test_line = translate(line, xoff=nx * 0.5, yoff=ny * 0.5)
            score = target_geom.intersection(test_line).length
            print(
                f"    - Testing normal {(nx, ny)} | Score (intersection length): {score:.4f}"
            )
            if score > best_score:
                best_score = score
                chosen_normal = (nx, ny)

        if chosen_normal is None or best_score == 0.0:
            print(
                f"  [EXTRUDE-FAIL] No valid normal found for {debug_label}. (Best score: {best_score})"
            )
            return None
        print(
            f"  [DECISION] Normal {chosen_normal} chosen via Scoring (Score: {best_score:.4f})"
        )

    # Binary search for extrusion distance
    nx, ny = chosen_normal
    low = 0.0
    high = max_distance
    print(f"  [DEBUG] Starting binary search. Max Target: {max_distance:.4f}")

    for i in range(14):
        mid_dist = (low + high) / 2.0
        test_line = translate(line, xoff=nx * mid_dist, yoff=ny * mid_dist)
        if test_line.within(target_geom):
            low = mid_dist
        else:
            high = mid_dist

    if low <= 0.01:
        print(
            f"  [EXTRUDE-BLOCKED] Final distance {low:.4f} too small for {debug_label}."
        )
        return None

    print(f"  [SUCCESS] Extrusion confirmed. Distance: {low:.4f}")
    shifted_coords = [(x + nx * low, y + ny * low) for x, y in coords]
    extrusion = Polygon(coords + list(reversed(shifted_coords)))

    if extrusion.is_empty:
        print(f"  [EXTRUDE-ERROR] Resulting polygon is empty for {debug_label}.")
        return None

    return extrusion.intersection(target_geom)


def extend_floor_plan_walls(floor_plan_data, filename=None) -> List[ProcessedRoomData]:
    print("\n" + "=" * 60)
    print(
        f"INITIALIZING HIERARCHY EXPANSION | Rooms to process: {len(floor_plan_data)}"
    )
    print("=" * 60)

    room_geoms = {
        i: box(room["x"], room["y"], room["x_end"], room["y_end"])
        for i, room in enumerate(floor_plan_data)
    }

    all_chosen_segments = []
    hierarchy_snapshots = []

    # Accessing global configuration (assuming ROOM_EXPAND_HIERARCHY and ROOM_EXPANSION_CONFIG exist)
    for room_type in ROOM_EXPAND_HIERARCHY:
        if room_type not in ROOM_EXPANSION_CONFIG:
            print(f"\n[SKIP] No config found for type: {room_type}")
            continue

        config = ROOM_EXPANSION_CONFIG[room_type]
        eligible_rooms = [
            (i, r) for i, r in enumerate(floor_plan_data) if r["type"] == room_type
        ]

        # Sort by area (smallest rooms often get priority in expansion logic)
        eligible_rooms.sort(key=lambda item: room_geoms[item[0]].area)
        rooms_to_process = eligible_rooms[: config["MAX_ROOMS_TO_EXPAND"]]

        print(f"\n--- PROCESSING HIERARCHY STEP: {room_type.upper()} ---")
        print(
            f"Eligible: {len(eligible_rooms)} | Processing Limit: {config['MAX_ROOMS_TO_EXPAND']}"
        )

        step_chosen_segments = []

        for i, room in rooms_to_process:
            print(f"\n[ROOM #{i}] Analyzing expansion for {room_type}...")

            # Re-calculate spaces because previous room expansions change the voids
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
                clean_geom = geom.buffer(0)
                inter = current_boundary.intersection(clean_geom.buffer(0.1))
                if geom.is_empty:
                    print(f"  [GEO-CHECK] {space_type} geom is empty. Skipping.")
                    continue

                # Small buffer to ensure intersection with boundary
                inter = current_boundary.intersection(geom.buffer(0))
                lines = getattr(inter, "geoms", [inter])

                print(
                    f"  [GEO-CHECK] Found {len(lines)} potential intersection segments with {space_type} voids."
                )

                for line_idx, line in enumerate(lines):
                    if isinstance(line, LineString):
                        original_length = line.length
                        work_line = line

                        # Apply length constraints
                        if original_length > config["MAX_WALL_LENGTH"]:
                            work_line = substring(line, 0, config["MAX_WALL_LENGTH"])
                            print(
                                f"    - Segment {line_idx}: Truncated {original_length:.2f} -> {work_line.length:.2f}"
                            )

                        if work_line.length >= config["MIN_WALL_LENGTH"]:
                            expandable_segments.append(
                                {
                                    "line": work_line,
                                    "type": space_type,
                                    "length": work_line.length,
                                    "target_geom": geom,
                                }
                            )
                        else:
                            print(
                                f"    - Segment {line_idx}: Ignored (too short: {work_line.length:.2f})"
                            )

            # Selection logic
            expandable_segments.sort(
                key=lambda x: (0 if x["type"] == "internal" else 1, -x["length"])
            )
            chosen_segments = expandable_segments[: config["MAX_SELECTIONS"]]
            print(
                f"  [DECISION] Selected {len(chosen_segments)} segments out of {len(expandable_segments)} available."
            )

            if chosen_segments:
                all_chosen_segments.extend(chosen_segments)
                step_chosen_segments.extend(chosen_segments)
                expanded_patches = []

                for seg_idx, seg in enumerate(chosen_segments):
                    calc_dist = seg["length"] * config["EXPANSION_PERCENTAGE"]
                    max_dist = min(calc_dist, config["EXPANSION_MAX_DISTANCE"])

                    label = f"room={i}_{room_type}_seg={seg_idx}_{seg['type']}"
                    patch = _extrude_wall_patch(
                        seg["line"],
                        seg["target_geom"],
                        max_dist,
                        label,
                    )

                    if patch is not None and not patch.is_empty:
                        expanded_patches.append(patch)

                if expanded_patches:
                    print(
                        f"  [UPDATE] Merging {len(expanded_patches)} new patches into Room #{i}."
                    )
                    room_geoms[i] = unary_union([current_poly] + expanded_patches)
                else:
                    print(f"  [UPDATE] No valid patches generated for Room #{i}.")

        hierarchy_snapshots.append(
            {
                "step_name": room_type,
                "room_geoms": room_geoms.copy(),
                "chosen_segments": step_chosen_segments,
            }
        )

    print("\n" + "=" * 60)
    print("EXPANSION PROCESS COMPLETE. CALCULATING FINAL SPACES.")
    print("=" * 60)

    (
        floor_union,
        orthogonal_envelope,
        all_holes,
        final_internal_voids,
        final_external_recesses,
    ) = _get_spaces(list(room_geoms.values()))

    if filename:
        print(f"[PLOT] Saving analysis plots to {filename}...")
        plot_step_progression(floor_plan_data, hierarchy_snapshots, filename=filename)
        _plot_side_by_side(
            floor_plan_data,
            orthogonal_envelope,
            all_holes,
            final_internal_voids,
            final_external_recesses,
            all_chosen_segments,
            room_geoms,
            filename,
        )
    final_plan = _get_reconstructed_data(floor_plan_data, room_geoms)
    print(f"\n Original Floor Plan Data: {floor_plan_data}\n")
    print(f"\n Final Plan Data (with vertices): {final_plan}\n")
    return final_plan

def _get_reconstructed_data(floor_plan_data, room_geoms) -> List[ProcessedRoomData]:
    reconstructed = []
    
    for i, room in enumerate(floor_plan_data):
        poly = room_geoms[i]
        
        # Extract the exterior coordinates as a list of (x, y) tuples
        # exterior.coords gives the sequence of points defining the wall
        vertices = list(poly.exterior.coords)
        
        # Create a new dictionary that preserves metadata but replaces bounds with vertices
        room_entry = ProcessedRoomData(
            type=room["type"],
            name=room.get("name", "NO_NAME"), # Default to type if name is missing
            original_index=i,
            vertices=vertices,
            area=poly.area
        )
        reconstructed.append(room_entry)
        
    return reconstructed


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
