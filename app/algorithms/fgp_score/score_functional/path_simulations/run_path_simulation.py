"""Path simulation orchestrator (public entry point).

Pipeline:
  1. Build room connectivity graph (nodes=rooms, edges=doors)
  2. Simulate 5 path classes through the graph — paths can ONLY travel
     via door openings, never through walls
  3. Analyse path overlaps and hallway utility
  4. Save a multi-panel diagnostic plot via temp_plotter
  5. Return PathScoreResult (scoring is a stub for now)

No imports from outside this package (except app.algorithms.types).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from shapely.geometry import LineString, Polygon

from app.algorithms.fgp_score.score_functional.path_simulations.dev.temp_plotter import (
    plot_path_simulation,
)
from app.algorithms.types.openings import FloorPlanWithOpenings

from . import path_sim_config
from .types import PathResult, PathScoreResult
from .util._dev_print import dev_print
from .util.room_graph import RoomGraph, build_room_graph

_WorldPt = Tuple[float, float]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _error_result(message: str) -> PathScoreResult:
    return PathScoreResult(
        total_score=0.0,
        circulation_efficiency=0.0,
        privacy_score=0.0,
        hallway_utility=0.0,
        furniture_flexibility=0.0,
        error=message,
    )


def _room_name_for_type(rooms: List[Any], rtype: str) -> Optional[str]:
    """Return the name of the first room matching rtype."""
    for r in rooms:
        if _get(r, "type", "") == rtype:
            return str(_get(r, "name", ""))
    return None


def _entry_room_name(rooms: List[Any], openings: List[Any]) -> Optional[str]:
    """Find the room name that the main door opens INTO (inside the house).

    Strategy:
      1. Find the opening with type containing 'main'
      2. Its connected_room (the non-veranda side) is the entry room
      3. Fallback: first livingRoom found
    """
    for op in openings:
        otype = str(_get(op, "opening_type", "")).lower()
        if "main" not in otype:
            continue
        rt = str(_get(op, "room_type", "")).lower()
        crt = str(_get(op, "connected_room_type", "")).lower()
        rn = str(_get(op, "room_name", ""))
        crn = str(_get(op, "connected_room_name", ""))

        # Pick whichever side is NOT outside/veranda
        if "veranda" in rt or "outside" in rt:
            return crn
        if "veranda" in crt or "outside" in crt:
            return rn
        # Both are interior rooms — pick the livingRoom side
        if "living" in rt:
            return rn
        if "living" in crt:
            return crn
        return crn  # fallback: connected room

    # No main door found — use first livingRoom
    return _room_name_for_type(rooms, "livingRoom")


def _run_one(
    graph: RoomGraph,
    label: str,
    color: str,
    start_room: str,
    end_room: str,
    is_public: bool = False,
) -> Optional[PathResult]:
    """Simulate one path and return PathResult, or None on failure."""
    coords = graph.find_path(start_room, end_room)
    if not coords or len(coords) < 2:
        dev_print("path", f"No path: {label!r}  ({start_room} -> {end_room})")
        return None
    dev_print("path", f"Path OK: {label!r}  {len(coords)} pts")
    return PathResult(label=label, coords=coords, color=color, is_public=is_public)


# ---------------------------------------------------------------------------
# Overlap analysis
# ---------------------------------------------------------------------------


def _analyse_overlaps(
    paths: List[PathResult],
    buffer_cm: float = 10.0,
) -> List[Dict[str, Any]]:
    """Return list of dicts describing pairs of paths that overlap/come close."""
    results: List[Dict[str, Any]] = []
    lines = []
    for p in paths:
        if len(p.coords) >= 2:
            lines.append((p.label, p.color, LineString(p.coords).buffer(buffer_cm)))
        else:
            lines.append((p.label, p.color, None))

    for i in range(len(lines)):
        la, ca, buf_a = lines[i]
        if buf_a is None:
            continue
        for j in range(i + 1, len(lines)):
            lb, cb, buf_b = lines[j]
            if buf_b is None:
                continue
            if buf_a.intersects(buf_b):
                overlap = buf_a.intersection(buf_b)
                results.append(
                    {
                        "path_a": la,
                        "path_b": lb,
                        "color_a": ca,
                        "color_b": cb,
                        "overlap_area": overlap.area,
                        "overlap_geom": overlap,
                    }
                )
    dev_print("path", f"Overlap analysis: {len(results)} overlapping pairs")
    return results


# ---------------------------------------------------------------------------
# Hallway utility analysis
# ---------------------------------------------------------------------------


def _analyse_hallway_utility(
    rooms: List[Any],
    paths: List[PathResult],
) -> Dict[str, Dict[str, Any]]:
    """For each hallway, count how many paths pass through it."""
    hallway_usage: Dict[str, Dict[str, Any]] = {}

    for room in rooms:
        rtype = str(_get(room, "type", ""))
        if rtype != "hallway":
            continue
        rname = str(_get(room, "name", "hallway"))
        verts = _get(room, "vertices", [])
        if len(verts) < 3:
            continue
        poly = Polygon(verts)
        crossing: List[str] = []
        for p in paths:
            if len(p.coords) >= 2:
                line = LineString(p.coords)
                if line.intersects(poly):
                    crossing.append(p.label)

        hallway_usage[rname] = {
            "count": len(crossing),
            "paths": crossing,
            "used": len(crossing) > 0,
            "polygon": poly,
        }

    dev_print("path", f"Hallway utility: { {k: v['count'] for k,v in hallway_usage.items()} }")
    return hallway_usage


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_path_simulation(
    floor_plan_with_openings: FloorPlanWithOpenings,
    score_margin: float = 100.0,
) -> PathScoreResult:
    """Run full path simulation pipeline.

    1. Build room connectivity graph
    2. Simulate 5 path classes (room-graph based — no wall crossing)
    3. Analyse overlaps and hallway utility
    4. Save diagnostic plot
    5. Return PathScoreResult (scoring stub — values are placeholders)
    """
    rooms: List[Any] = _get(floor_plan_with_openings, "floor_plan", [])
    openings: List[Any] = _get(floor_plan_with_openings, "openings", [])

    dev_print("path", f"Starting simulation: {len(rooms)} rooms, {len(openings)} openings.")

    if not rooms:
        return _error_result("No rooms provided.")

    # ------------------------------------------------------------------
    # 1. Build room graph
    # ------------------------------------------------------------------
    dev_print("path", "Building room connectivity graph...")
    graph = build_room_graph(rooms, openings)

    # ------------------------------------------------------------------
    # 2. Determine entry room (inside main door)
    # ------------------------------------------------------------------
    entry_room = _entry_room_name(rooms, openings)
    if not entry_room:
        return _error_result("Cannot determine entry room.")
    dev_print("path", f"Entry room: {entry_room!r}")

    # ------------------------------------------------------------------
    # 3. Run simulation classes
    # ------------------------------------------------------------------
    paths: List[PathResult] = []

    bedroom_rooms = [r for r in rooms if _get(r, "type", "") == "bedroom"]
    bathroom_rooms = [r for r in rooms if _get(r, "type", "") in ("bathroom", "attachedBathroom")]
    kitchen_rooms = [r for r in rooms if _get(r, "type", "") == "kitchen"]

    # Class 1: Entry -> Kitchen
    if kitchen_rooms:
        k_name = str(_get(kitchen_rooms[0], "name", ""))
        res = _run_one(
            graph, "Entry->Kitchen",
            path_sim_config.PATH_COLORS["entry_kitchen"],
            entry_room, k_name, is_public=True,
        )
        if res:
            paths.append(res)

    # Class 2: Entry -> Each Bedroom
    for idx, room in enumerate(bedroom_rooms):
        rname = str(_get(room, "name", ""))
        res = _run_one(
            graph, f"Entry->Bed {idx + 1}",
            path_sim_config.PATH_COLORS["entry_bedroom"],
            entry_room, rname, is_public=False,
        )
        if res:
            paths.append(res)

    # Class 3: Entry -> Each Bathroom
    for idx, room in enumerate(bathroom_rooms):
        rname = str(_get(room, "name", ""))
        res = _run_one(
            graph, f"Entry->Bath {idx + 1}",
            path_sim_config.PATH_COLORS["entry_bathroom"],
            entry_room, rname, is_public=True,
        )
        if res:
            paths.append(res)

    # Class 4: Each Bedroom -> Nearest Bathroom
    for b_idx, bed_room in enumerate(bedroom_rooms):
        bed_name = str(_get(bed_room, "name", ""))
        bed_c = graph.get_centroid(bed_name)
        if not bed_c or not bathroom_rooms:
            continue

        # Find nearest bathroom by Euclidean distance
        best_bath = min(
            bathroom_rooms,
            key=lambda r: math.sqrt(
                (graph.get_centroid(str(_get(r, "name", "")))[0] - bed_c[0]) ** 2
                + (graph.get_centroid(str(_get(r, "name", "")))[1] - bed_c[1]) ** 2
                if graph.get_centroid(str(_get(r, "name", ""))) else float("inf")
            ),
        )
        ba_name = str(_get(best_bath, "name", ""))
        res = _run_one(
            graph, f"Bed {b_idx + 1}->Bath",
            path_sim_config.PATH_COLORS["bedroom_bathroom"],
            bed_name, ba_name, is_public=False,
        )
        if res:
            paths.append(res)

    # Class 5: Each Bedroom -> Kitchen
    if kitchen_rooms:
        k_name = str(_get(kitchen_rooms[0], "name", ""))
        for b_idx, bed_room in enumerate(bedroom_rooms):
            bed_name = str(_get(bed_room, "name", ""))
            res = _run_one(
                graph, f"Bed {b_idx + 1}->Kitchen",
                path_sim_config.PATH_COLORS["bedroom_kitchen"],
                bed_name, k_name, is_public=False,
            )
            if res:
                paths.append(res)

    dev_print("path", f"Total paths simulated: {len(paths)}")

    if not paths:
        return _error_result("No valid paths found.")

    # ------------------------------------------------------------------
    # 4. Overlap analysis + hallway utility
    # ------------------------------------------------------------------
    overlaps = _analyse_overlaps(paths, buffer_cm=10.0)
    hallway_usage = _analyse_hallway_utility(rooms, paths)

    # ------------------------------------------------------------------
    # 5. Save diagnostic plot
    # ------------------------------------------------------------------
    try:
        plot_path = plot_path_simulation(
            rooms=rooms,
            openings=openings,
            paths=paths,
            overlaps=overlaps,
            hallway_usage=hallway_usage,
            output_dir=None,  # uses dev/output default
        )
        dev_print("path", f"Plot saved: {plot_path}")
    except Exception as exc:
        dev_print("path", f"Plot failed: {exc}")
        import traceback
        traceback.print_exc()
        plot_path = ""

    # ------------------------------------------------------------------
    # 6. Stub scoring (placeholder — to be implemented separately)
    # ------------------------------------------------------------------
    total_unused_hallways = sum(
        1 for v in hallway_usage.values() if not v["used"]
    )
    hallway_score = max(0.0, 25.0 - total_unused_hallways * 10.0)

    overlap_penalty = min(30.0, len(overlaps) * 3.0)
    circulation_score = max(0.0, 30.0 - overlap_penalty)

    total = round(circulation_score + hallway_score, 2)

    dev_print("path", {
        "paths_found": len(paths),
        "overlapping_pairs": len(overlaps),
        "unused_hallways": total_unused_hallways,
        "stub_total_score": total,
    })

    return PathScoreResult(
        total_score=total,
        circulation_efficiency=circulation_score,
        privacy_score=0.0,   # TODO
        hallway_utility=hallway_score,
        furniture_flexibility=0.0,  # TODO
        paths=paths,
        details={
            "overlaps": [
                {"path_a": o["path_a"], "path_b": o["path_b"], "overlap_area": o["overlap_area"]}
                for o in overlaps
            ],
            "hallway_usage": {
                k: {"count": v["count"], "paths": v["paths"], "used": v["used"]}
                for k, v in hallway_usage.items()
            },
        },
        plot_path=plot_path,
    )
