"""Path simulation orchestrator (dev/test entry point).

Runs all 5 heuristic simulation classes, scores the result,
and optionally saves the 3-panel debug PNG.

Called from score_manager.py for testing before full integration.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..nav_mesh import build_nav_mesh
from ..pathfinder import AStarGrid
from ..scorer import score_path_simulation
from ..simulation_points import extract_simulation_points, nearest_bathroom_key
from ..types import PathResult, PathScoreResult
from .plotter import save_path_score_plot

# Threshold – plot is saved only when score exceeds this value
PATH_SCORE_PLOT_SCORE_MARGIN: float = 40.0

# Path colour palette (one per simulation class)
_COLOURS: Dict[str, str] = {
    "entry_kitchen":    "#FF6B35",
    "entry_bedroom":    "#4ECDC4",
    "entry_bathroom":   "#45B7D1",
    "bedroom_bathroom": "#96CEB4",
    "bedroom_kitchen":  "#FFEAA7",
}

# Grid resolution in cm – 15cm balances detail vs. speed
_RESOLUTION: float = 15.0


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
        print(f"[path_sim] WARNING: no path found for '{label}'")
        return None
    return PathResult(label=label, coords=coords, color=color, is_public=is_public)


def run_path_simulation_dev(
    floor_plan_with_openings: Any,
) -> PathScoreResult:
    """Run full path simulation pipeline.

    Parameters
    ----------
    floor_plan_with_openings:
        FloorPlanWithOpenings dataclass with .floor_plan and .openings.

    Returns
    -------
    PathScoreResult with total_score (0–100) and optional plot_path.
    """
    rooms: List[Any] = getattr(floor_plan_with_openings, "floor_plan", [])
    openings: List[Any] = getattr(floor_plan_with_openings, "openings", [])

    if not rooms:
        return PathScoreResult(
            total_score=0.0,
            circulation_efficiency=0.0,
            privacy_score=0.0,
            hallway_utility=0.0,
            furniture_flexibility=0.0,
            error="No rooms provided.",
        )

    # ------------------------------------------------------------------
    # 1. Build navigation mesh
    # ------------------------------------------------------------------
    print("[path_sim] Building navigation mesh …")
    nav_mesh, total_floor = build_nav_mesh(rooms, openings)

    if nav_mesh.is_empty:
        return PathScoreResult(
            total_score=0.0,
            circulation_efficiency=0.0,
            privacy_score=0.0,
            hallway_utility=0.0,
            furniture_flexibility=0.0,
            error="Navigation mesh is empty.",
        )

    # ------------------------------------------------------------------
    # 2. Rasterise + label room types
    # ------------------------------------------------------------------
    print("[path_sim] Rasterizing grid …")
    grid = AStarGrid(resolution=_RESOLUTION)
    grid.rasterize(nav_mesh)
    grid.label_room_types(rooms)

    # ------------------------------------------------------------------
    # 3. Extract simulation anchor points
    # ------------------------------------------------------------------
    print("[path_sim] Extracting simulation anchor points …")
    sim_points = extract_simulation_points(rooms, openings)

    if "front_door" not in sim_points:
        print("[path_sim] WARNING: front door anchor not found – attempting fallback …")
        # Fallback: use centroid of first livingRoom
        for room in rooms:
            if getattr(room, "type", "") == "livingRoom":
                verts = getattr(room, "vertices", [])
                if verts:
                    xs = [v[0] for v in verts]
                    ys = [v[1] for v in verts]
                    sim_points["front_door"] = (sum(xs) / len(xs), sum(ys) / len(ys))
                    break

    if "front_door" not in sim_points:
        return PathScoreResult(
            total_score=0.0,
            circulation_efficiency=0.0,
            privacy_score=0.0,
            hallway_utility=0.0,
            furniture_flexibility=0.0,
            error="Cannot determine front door anchor – simulation aborted.",
        )

    front_door = sim_points["front_door"]
    paths: List[PathResult] = []

    # ------------------------------------------------------------------
    # 4. Run the 5 simulation classes
    # ------------------------------------------------------------------

    # Class 1: Front Door → Kitchen
    if "kitchen" in sim_points:
        result = _run_one(
            grid, "Entry→Kitchen", _COLOURS["entry_kitchen"],
            front_door, sim_points["kitchen"], is_public=True,
        )
        if result:
            paths.append(result)

    # Class 2: Front Door → Every Bedroom
    bedroom_keys = sorted(k for k in sim_points if k.startswith("bedroom_"))
    for bk in bedroom_keys:
        idx = bk.split("_")[1]
        result = _run_one(
            grid, f"Entry→Bedroom {idx}", _COLOURS["entry_bedroom"],
            front_door, sim_points[bk], is_public=False,
        )
        if result:
            paths.append(result)

    # Class 3: Front Door → Every Bathroom
    bathroom_keys = sorted(k for k in sim_points if k.startswith("bathroom_"))
    for bk in bathroom_keys:
        idx = bk.split("_")[1]
        result = _run_one(
            grid, f"Entry→Bathroom {idx}", _COLOURS["entry_bathroom"],
            front_door, sim_points[bk], is_public=True,
        )
        if result:
            paths.append(result)

    # Class 4: Each Bedroom → Nearest Bathroom
    for bed_key in bedroom_keys:
        bath_key = nearest_bathroom_key(bed_key, sim_points)
        if bath_key is None:
            continue
        b_idx = bed_key.split("_")[1]
        ba_idx = bath_key.split("_")[1]
        result = _run_one(
            grid, f"Bed {b_idx}→Bath {ba_idx}", _COLOURS["bedroom_bathroom"],
            sim_points[bed_key], sim_points[bath_key], is_public=False,
        )
        if result:
            paths.append(result)

    # Class 5: Each Bedroom → Kitchen
    if "kitchen" in sim_points:
        for bed_key in bedroom_keys:
            b_idx = bed_key.split("_")[1]
            result = _run_one(
                grid, f"Bed {b_idx}→Kitchen", _COLOURS["bedroom_kitchen"],
                sim_points[bed_key], sim_points["kitchen"], is_public=False,
            )
            if result:
                paths.append(result)

    print(f"[path_sim] Simulated {len(paths)} paths.")

    # ------------------------------------------------------------------
    # 5. Score
    # ------------------------------------------------------------------
    bedroom_door_pts = [sim_points[k] for k in bedroom_keys if k in sim_points]
    score_result = score_path_simulation(grid, paths, bedroom_door_pts)

    print(
        f"[path_sim] Score: {score_result.total_score:.1f}/100  "
        f"(Circ={score_result.circulation_efficiency:.1f}  "
        f"Priv={score_result.privacy_score:.1f}  "
        f"Hall={score_result.hallway_utility:.1f}  "
        f"Furn={score_result.furniture_flexibility:.1f})"
    )

    # ------------------------------------------------------------------
    # 6. Plot (only when score exceeds margin)
    # ------------------------------------------------------------------
    if score_result.total_score > PATH_SCORE_PLOT_SCORE_MARGIN:
        try:
            plot_path = save_path_score_plot(grid, score_result, rooms)
            score_result.plot_path = plot_path
            print(f"[path_sim] Plot saved: {plot_path}")
        except Exception as exc:
            print(f"[path_sim] Plot generation failed: {exc}")

    return score_result