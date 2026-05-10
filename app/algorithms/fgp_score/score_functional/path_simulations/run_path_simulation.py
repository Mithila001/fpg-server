"""Path simulation orchestrator (public entry point).

Runs all 5 heuristic simulation classes, scores the result,
and optionally saves a 4-panel debug PNG.
"""

from __future__ import annotations

from typing import Any, List, Tuple

from app.algorithms.fgp_score.score_functional.path_simulations.dev.temp_plotter import (
    plot_nav_mesh,
)
from app.algorithms.types.openings import FloorPlanWithOpenings

from . import path_sim_config
from .util._dev_print import dev_print
from .util.nav_mesh import build_nav_mesh
from .util.pathfinder import AStarGrid
from test.plotters.path_plotter import save_path_score_plot, save_path_only_grid_plot
from .util.scorer import score_path_simulation
from .util.simulation_points import extract_simulation_points, nearest_bathroom_key
from .types import PathResult, PathScoreResult


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _run_one(
    grid: AStarGrid,
    label: str,
    color: str,
    start: Tuple[float, float],
    end: Tuple[float, float],
    is_public: bool = False,
) -> PathResult | None:
    """Run A* for one pair and return a PathResult, or None if no path found."""
    coords = grid.find_path(start, end)
    if not coords:
        dev_print("path", f"WARNING: No path found for '{label}' from {start} to {end}")
        return None

    dev_print("path", f"Success: Path found for '{label}' ({len(coords)} nodes)")
    return PathResult(label=label, coords=coords, color=color, is_public=is_public)


def _error_result(message: str) -> PathScoreResult:
    return PathScoreResult(
        total_score=0.0,
        circulation_efficiency=0.0,
        privacy_score=0.0,
        hallway_utility=0.0,
        furniture_flexibility=0.0,
        error=message,
    )


def run_path_simulation(
    floor_plan_with_openings: FloorPlanWithOpenings, score_margin: float = 100.0
) -> PathScoreResult:
    """Run full path simulation pipeline.

    Parameters
    ----------
    floor_plan_with_openings:
        Either a dict or a dataclass-like object with floor_plan and openings.
    score_margin:
        Margin to normalize final scores. Default 100.0 keeps scores unchanged.
        Values are normalized as: normalized_score = (raw_score / 100) * score_margin

    Returns
    -------
    PathScoreResult with total_score (0-score_margin) and optional plot_path.
    """

    rooms: List[Any] = _get(floor_plan_with_openings, "floor_plan", [])
    openings: List[Any] = _get(floor_plan_with_openings, "openings", [])

    dev_print(
        "path",
        f"Starting simulation: {len(rooms)} rooms, {len(openings)} openings found.",
    )

    if not rooms:
        dev_print("path", "ERROR: No rooms provided.")
        return _error_result("No rooms provided.")

    # ------------------------------------------------------------------
    # 1. Build navigation mesh
    # ------------------------------------------------------------------
    dev_print("path", "Building navigation mesh...")
    nav_mesh, total_floor = build_nav_mesh(rooms, openings)

    if nav_mesh.is_empty:
        dev_print("path", "ERROR: Navigation mesh is empty.")
        return _error_result("Navigation mesh is empty.")
    dev_print("path", f"Nav mesh built. Total floor area: {total_floor.area:.2f}")

    # ------------------------------------------------------------------
    # 2. Rasterize + label room types
    # ------------------------------------------------------------------
    dev_print(
        "path",
        f"Rasterizing grid at {path_sim_config.GRID_RESOLUTION_CM}cm resolution...",
    )
    grid = AStarGrid(resolution=path_sim_config.GRID_RESOLUTION_CM)
    grid.rasterize(nav_mesh)
    grid.label_room_types(rooms)
    dev_print("path", f"Grid rasterized. Bounds: {grid.width}x{grid.height} nodes.")

    # ------------------------------------------------------------------
    # 3. Extract simulation anchor points
    # ------------------------------------------------------------------
    dev_print("path", "Extracting simulation anchor points...")
    sim_points = extract_simulation_points(rooms, openings)
    dev_print("path", f"Anchor points found: {list(sim_points.keys())}")

    if "front_door" not in sim_points:
        dev_print(
            "path",
            "WARNING: front door anchor not found – attempting fallback to Living Room...",
        )
        for room in rooms:
            if _get(room, "type", "") == "livingRoom":
                verts = _get(room, "vertices", [])
                if verts:
                    xs = [v[0] for v in verts]
                    ys = [v[1] for v in verts]
                    sim_points["front_door"] = (sum(xs) / len(xs), sum(ys) / len(ys))
                    dev_print(
                        "path",
                        "Fallback success: Front door set to Living Room centroid "
                        f"{sim_points['front_door']}",
                    )
                    break

    # If still not found, try scanning openings for a main/outside door
    if "front_door" not in sim_points:
        for op in openings:
            optype = str(_get(op, "opening_type", "")).lower()
            rn = str(_get(op, "room_name", "")).upper()
            crn = str(_get(op, "connected_room_name", "")).upper()
            if "main" in optype or rn == "OUTSIDE" or crn == "OUTSIDE":
                sim_points["front_door"] = (
                    (float(_get(op, "x1", 0.0)) + float(_get(op, "x2", 0.0))) / 2.0,
                    (float(_get(op, "y1", 0.0)) + float(_get(op, "y2", 0.0))) / 2.0,
                )
                dev_print(
                    "path",
                    f"Fallback: front_door located via openings at {sim_points['front_door']}",
                )
                break

    if "front_door" not in sim_points:
        dev_print(
            "path",
            "CRITICAL ERROR: Cannot determine front door anchor – simulation aborted.",
        )
        return _error_result("Cannot determine front door anchor – simulation aborted.")

    paths: List[PathResult] = []

    # Helper: compute room centroid
    def _room_centroid(room: Any) -> Tuple[float, float]:
        verts = _get(room, "vertices", [])
        if not verts:
            return (0.0, 0.0)
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    # Prepare typed lists to resolve keys -> room objects
    bedroom_rooms = [r for r in rooms if _get(r, "type", "") == "bedroom"]
    bathroom_rooms = [
        r for r in rooms if _get(r, "type", "") in ("bathroom", "attachedBathroom")
    ]
    kitchen_rooms = [r for r in rooms if _get(r, "type", "") == "kitchen"]

    def coord_for_key(key: str) -> Tuple[float, float]:
        # Entrance
        if key == "front_door":
            return sim_points["front_door"]
        # Kitchen -> room center if exists
        if key == "kitchen":
            if kitchen_rooms:
                return _room_centroid(kitchen_rooms[0])
            return sim_points.get("kitchen", (0.0, 0.0))
        # Bedrooms
        if key.startswith("bedroom_"):
            try:
                idx = int(key.split("_")[1])
                return _room_centroid(bedroom_rooms[idx])
            except Exception:
                return sim_points.get(key, (0.0, 0.0))
        # Bathrooms
        if key.startswith("bathroom_"):
            try:
                idx = int(key.split("_")[1])
                return _room_centroid(bathroom_rooms[idx])
            except Exception:
                return sim_points.get(key, (0.0, 0.0))
        # Fallback to whatever sim_points returned
        return sim_points.get(key, (0.0, 0.0))

    # ------------------------------------------------------------------
    # 4. Run the 5 simulation classes
    # ------------------------------------------------------------------
    dev_print("path", "Executing simulation classes...")

    # Class 1: Front Door -> Kitchen
    if "kitchen" in sim_points:
        result = _run_one(
            grid,
            "Entry->Kitchen",
            path_sim_config.PATH_COLORS["entry_kitchen"],
            coord_for_key("front_door"),
            coord_for_key("kitchen"),
            is_public=True,
        )
        if result:
            paths.append(result)

    # Class 2: Front Door -> Every Bedroom
    bedroom_keys = sorted(k for k in sim_points if k.startswith("bedroom_"))
    for bk in bedroom_keys:
        idx = bk.split("_")[1]
        result = _run_one(
            grid,
            f"Entry->Bedroom {idx}",
            path_sim_config.PATH_COLORS["entry_bedroom"],
            coord_for_key("front_door"),
            coord_for_key(bk),
            is_public=False,
        )
        if result:
            paths.append(result)

    # Class 3: Front Door -> Every Bathroom
    bathroom_keys = sorted(k for k in sim_points if k.startswith("bathroom_"))
    for bk in bathroom_keys:
        idx = bk.split("_")[1]
        result = _run_one(
            grid,
            f"Entry->Bathroom {idx}",
            path_sim_config.PATH_COLORS["entry_bathroom"],
            coord_for_key("front_door"),
            coord_for_key(bk),
            is_public=True,
        )
        if result:
            paths.append(result)

    # Class 4: Each Bedroom -> Nearest Bathroom
    for bed_key in bedroom_keys:
        bath_key = nearest_bathroom_key(bed_key, sim_points)
        if bath_key is None:
            dev_print("path", f"Notice: No nearby bathroom found for {bed_key}")
            continue
        b_idx = bed_key.split("_")[1]
        ba_idx = bath_key.split("_")[1]
        result = _run_one(
            grid,
            f"Bed {b_idx}->Bath {ba_idx}",
            path_sim_config.PATH_COLORS["bedroom_bathroom"],
            coord_for_key(bed_key),
            coord_for_key(bath_key),
            is_public=False,
        )
        if result:
            paths.append(result)

    # Class 5: Each Bedroom -> Kitchen
    if "kitchen" in sim_points:
        for bed_key in bedroom_keys:
            b_idx = bed_key.split("_")[1]
            result = _run_one(
                grid,
                f"Bed {b_idx}->Kitchen",
                path_sim_config.PATH_COLORS["bedroom_kitchen"],
                coord_for_key(bed_key),
                coord_for_key("kitchen"),
                is_public=False,
            )
            if result:
                paths.append(result)

    dev_print("path", f"Simulated {len(paths)} total paths successfully.")

    if not paths:
        dev_print("path", "ERROR: No valid paths found. Simulation aborted.")
        return _error_result("No valid paths found.")

    # ------------------------------------------------------------------
    # 5. Score
    # ------------------------------------------------------------------
    dev_print("path", "Calculating final scores...")
    bedroom_door_pts = [sim_points[k] for k in bedroom_keys if k in sim_points]
    score_result = score_path_simulation(grid, paths, bedroom_door_pts, score_margin)

    dev_print(
        "path",
        {
            "total_score": score_result.total_score,
            "circulation": score_result.circulation_efficiency,
            "privacy": score_result.privacy_score,
            "hallway": score_result.hallway_utility,
            "furniture": score_result.furniture_flexibility,
        },
    )

    plot_path = plot_nav_mesh(
        nav_mesh=nav_mesh,
        total_floor=total_floor,
        rooms=rooms,
        output_dir=None,  # Uses default dev/output directory
    )

    # ------------------------------------------------------------------
    # 6. Plot (only when score exceeds margin)
    # ------------------------------------------------------------------
    if score_result.total_score > path_sim_config.PATH_SCORE_PLOT_SCORE_MARGIN:
        try:
            dev_print(
                "path",
                f"Score {score_result.total_score:.1f} > margin. Generating debug plot...",
            )
            plot_path = save_path_score_plot(grid, score_result, rooms)
            score_result.plot_path = plot_path
            dev_print("path", f"Plot saved to: {plot_path}")

            path_only_plot_path = save_path_only_grid_plot(score_result, rooms)
            score_result.details["path_only_plot_path"] = path_only_plot_path
            dev_print("path", f"Path-only grid plot saved to: {path_only_plot_path}")
        except Exception as exc:
            dev_print("path", f"ERROR: Plot generation failed: {exc}")
    else:
        dev_print(
            "path",
            f"Score {score_result.total_score:.1f} below margin "
            f"({path_sim_config.PATH_SCORE_PLOT_SCORE_MARGIN}). Skipping plot.",
        )

    return score_result
