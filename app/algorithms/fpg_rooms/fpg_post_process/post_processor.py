from __future__ import annotations

from .processors import build_compact_data, run_wall_union, snap_solution_rooms_to_grid
from .types import (
    PostProcessInputPayload,
    PostProcessOutputPayload,
    ProcessContextPayload,
    QuickPostProcessOutputPayload,
)
from .utils import normalize_openings, normalize_rooms


def run_final_post_process(payload: PostProcessInputPayload) -> PostProcessOutputPayload:
    """Heavy Post processor for finalize the data"""
    context: ProcessContextPayload = {
        "rooms": normalize_rooms(payload.get("rooms", [])),
        "openings": normalize_openings(payload.get("openings", [])),
        "tolerance": float(payload.get("tolerance", 1e-6)),
        "wall_union": payload.get("wall_union"),
    }

    wall_union_result = context.get("wall_union") or {"walls": [], "room_walls": {}}
    compact_by_room = build_compact_data(
        wall_union=wall_union_result,
        openings=context["openings"],
        rooms=context["rooms"],
    )

    return {
        "status": "SUCCESS",
        "message": "Post-processing pipeline completed",
        "walls": wall_union_result["walls"],
        "compact_by_room": compact_by_room,
    }


def run_quick_post_process(payload: PostProcessInputPayload) -> QuickPostProcessOutputPayload:
    """Post Process function for iterative post processing for algorithms"""
    context: ProcessContextPayload = {
        "rooms": normalize_rooms(payload.get("rooms", [])),
        "openings": [],
        "tolerance": float(payload.get("tolerance", 1e-6)),
    }

    snapped_rooms = snap_solution_rooms_to_grid(context["rooms"], grid_size=8.0)

    wall_union_result = run_wall_union(
        rooms=snapped_rooms,
        tolerance=context["tolerance"],
    )

    return {
        "status": "SUCCESS",
        "message": "Quick post-processing completed",
        "rooms": snapped_rooms,
        "wall_union": wall_union_result,
    }

