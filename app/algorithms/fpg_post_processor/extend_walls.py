from typing import List
from shapely.affinity import translate
from shapely.geometry import box, MultiPolygon, Polygon, LineString
from shapely.ops import unary_union, substring
from app.algorithms.types.domain import ProcessedRoomData

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

ROOM_EXPAND_HIERARCHY = ["veranda", "livingRoom", "kitchen", "hallway", "bedroom"]

ROOM_EXPANSION_CONFIG = {
    "livingRoom": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": 40,
        "MAX_ROOMS_TO_EXPAND": 1,
        "MAX_SELECTIONS": 2,
        "EXPANSION_PERCENTAGE": 0.80,
        "EXPANSION_MAX_DISTANCE": 20,
    },
    "kitchen": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": 40,
        "MAX_ROOMS_TO_EXPAND": 1,
        "MAX_SELECTIONS": 1,
        "EXPANSION_PERCENTAGE": 0.80,
        "EXPANSION_MAX_DISTANCE": 10,
    },
    "hallway": {
        "MIN_WALL_LENGTH": 5,
        "MAX_WALL_LENGTH": 50,
        "MAX_ROOMS_TO_EXPAND": 3,
        "MAX_SELECTIONS": 3,
        "EXPANSION_PERCENTAGE": 0.80,
        "EXPANSION_MAX_DISTANCE": 2,
    },
    "bedroom": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": 40,
        "MAX_ROOMS_TO_EXPAND": 3,
        "MAX_SELECTIONS": 1,
        "EXPANSION_PERCENTAGE": 0.80,
        "EXPANSION_MAX_DISTANCE": 10,
    },
    "veranda": {
        "MIN_WALL_LENGTH": 10,
        "MAX_WALL_LENGTH": 50,
        "MAX_ROOMS_TO_EXPAND": 3,
        "MAX_SELECTIONS": 1,
        "EXPANSION_PERCENTAGE": 0.80,
        "EXPANSION_MAX_DISTANCE": 40,
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
        for poly in floor_union.geoms:  # type: ignore
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
    if line.is_empty or target_geom.is_empty:
        return None

    coords = list(line.coords)
    if len(coords) < 2:
        return None

    x1, y1 = coords[0]
    x2, y2 = coords[-1]
    dx = x2 - x1
    dy = y2 - y1

    if abs(dx) >= abs(dy):
        normals = [(0.0, 1.0), (0.0, -1.0)]
    else:
        normals = [(1.0, 0.0), (-1.0, 0.0)]

    mid = line.interpolate(0.5, normalized=True)
    chosen_normal = None

    # Phase 1: Direct containment probe
    for nx, ny in normals:
        probe = translate(mid, xoff=nx * 0.5, yoff=ny * 0.5)
        if target_geom.contains(probe):
            chosen_normal = (nx, ny)
            break

    # Phase 2: Intersection scoring (if Phase 1 fails)
    if chosen_normal is None:
        best_score = 0.0
        for nx, ny in normals:
            test_line = translate(line, xoff=nx * 0.5, yoff=ny * 0.5)
            score = target_geom.intersection(test_line).length
            if score > best_score:
                best_score = score
                chosen_normal = (nx, ny)

        if chosen_normal is None or best_score == 0.0:
            return None

    # Binary search for extrusion distance
    nx, ny = chosen_normal
    low = 0.0
    high = max_distance

    for i in range(14):
        mid_dist = (low + high) / 2.0
        test_line = translate(line, xoff=nx * mid_dist, yoff=ny * mid_dist)
        if test_line.within(target_geom):
            low = mid_dist
        else:
            high = mid_dist

    if low <= 0.01:
        return None

    shifted_coords = [(x + nx * low, y + ny * low) for x, y in coords]
    extrusion = Polygon(coords + list(reversed(shifted_coords)))

    if extrusion.is_empty:
        return None

    return extrusion.intersection(target_geom)


def extend_floor_plan_walls(floor_plan_data, filename=None) -> List[ProcessedRoomData]:
    room_geoms = {
        i: box(room["x"], room["y"], room["x_end"], room["y_end"])
        for i, room in enumerate(floor_plan_data)
    }

    for room_type in ROOM_EXPAND_HIERARCHY:
        if room_type not in ROOM_EXPANSION_CONFIG:
            continue

        config = ROOM_EXPANSION_CONFIG[room_type]
        eligible_rooms = [
            (i, r) for i, r in enumerate(floor_plan_data) if r["type"] == room_type
        ]

        # Sort by area (smallest rooms often get priority in expansion logic)
        eligible_rooms.sort(key=lambda item: room_geoms[item[0]].area)
        rooms_to_process = eligible_rooms[: config["MAX_ROOMS_TO_EXPAND"]]

        for i, room in rooms_to_process:
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
                if geom.is_empty:
                    continue

                # Small buffer to ensure intersection with boundary
                inter = current_boundary.intersection(geom.buffer(0))
                lines = getattr(inter, "geoms", [inter])

                for line_idx, line in enumerate(lines):
                    if isinstance(line, LineString):
                        original_length = line.length
                        work_line = line

                        # Apply length constraints
                        if original_length > config["MAX_WALL_LENGTH"]:
                            work_line = substring(line, 0, config["MAX_WALL_LENGTH"])

                        if work_line.length >= config["MIN_WALL_LENGTH"]:
                            expandable_segments.append(
                                {
                                    "line": work_line,
                                    "type": space_type,
                                    "length": work_line.length,
                                    "target_geom": geom,
                                }
                            )

            # Selection logic
            expandable_segments.sort(
                key=lambda x: (0 if x["type"] == "internal" else 1, -x["length"])
            )
            chosen_segments = expandable_segments[: config["MAX_SELECTIONS"]]

            if chosen_segments:
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
                    room_geoms[i] = unary_union([current_poly] + expanded_patches)

    return _get_reconstructed_data(floor_plan_data, room_geoms)


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
            name=room.get("name", "NO_NAME"),  # Default to type if name is missing
            original_index=i,
            vertices=vertices,
            area=poly.area,
        )
        reconstructed.append(room_entry)

    return reconstructed

