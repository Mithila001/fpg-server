from __future__ import annotations

from .processors import build_compact_data, run_wall_union
from .types import (
    PostProcessInputPayload,
    PostProcessOutputPayload,
    ProcessContextPayload,
)
from .utils import normalize_openings, normalize_rooms


def run_post_processor(payload: PostProcessInputPayload) -> PostProcessOutputPayload:
    """Run the room post-processing pipeline and return API-ready payload."""
    context: ProcessContextPayload = {
        "rooms": normalize_rooms(payload.get("rooms", [])),
        "openings": normalize_openings(payload.get("openings", [])),
        "tolerance": float(payload.get("tolerance", 1e-6)),
    }

    wall_union_result = run_wall_union(
        rooms=context["rooms"],
        tolerance=context["tolerance"],
    )
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
