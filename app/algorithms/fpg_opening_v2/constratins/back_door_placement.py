from __future__ import annotations

from app.algorithms.fpg_opening_v2.constratins.main_door_to_outside import (
    ExteriorSegmentCandidate,
    build_exterior_segment_candidates,
)
from app.algorithms.types.domain import ProcessedRoomData
from app.algorithms.types.openings import OpeningData
from app.core.fpg_opening_config import (
    BACK_DOOR_ELIGIBLE_ROOM_TYPES,
    BACK_DOOR_ROOM_TYPE_PRIORITY,
    normalize_room_type,
)


def _segment_length(candidate: ExteriorSegmentCandidate) -> float:
    segment = candidate.segment
    if abs(segment.y1 - segment.y2) < 1e-6:
        return abs(segment.x2 - segment.x1)
    return abs(segment.y2 - segment.y1)


def select_back_door(
    floor_plan: list[ProcessedRoomData],
    preferred_door_length: float,
    existing_openings: list[OpeningData],
    tolerance: float = 1e-6,
) -> OpeningData | None:
    exterior = build_exterior_segment_candidates(floor_plan, tolerance=tolerance)
    eligible = [
        candidate
        for candidate in exterior
        if normalize_room_type(candidate.room.type) in BACK_DOOR_ELIGIBLE_ROOM_TYPES
    ]
    if not eligible:
        return None

    # Avoid choosing the exact same wall already used by another door.
    occupied = {
        (opening.room_name, opening.side)
        for opening in existing_openings
        if opening.opening_type in {"mainDoor", "internalDoor"}
    }
    filtered = [
        candidate
        for candidate in eligible
        if (candidate.room.name, candidate.side) not in occupied
    ]
    candidate_pool = filtered if filtered else eligible
    if not candidate_pool:
        return None

    ranked = sorted(
        candidate_pool,
        key=lambda c: (
            BACK_DOOR_ROOM_TYPE_PRIORITY.get(normalize_room_type(c.room.type), 99),
            0 if c.side == "north" else (1 if c.side in {"west", "east"} else 2),
            c.room.name,
        ),
    )
    selected = ranked[0]
    segment = selected.segment
    seg_len = _segment_length(selected)
    if seg_len <= tolerance:
        return None
    door_len = min(preferred_door_length, seg_len)
    if abs(segment.y1 - segment.y2) < 1e-6:
        mid = (segment.x1 + segment.x2) / 2.0
        x1 = mid - door_len / 2.0
        x2 = mid + door_len / 2.0
        y1 = segment.y1
        y2 = segment.y2
    else:
        mid = (segment.y1 + segment.y2) / 2.0
        y1 = mid - door_len / 2.0
        y2 = mid + door_len / 2.0
        x1 = segment.x1
        x2 = segment.x2

    return OpeningData(
        room_name=selected.room.name,
        room_type=selected.room.type,
        opening_type="backDoor",
        side=selected.side,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        connected_room_name="OUTSIDE",
        connected_room_type="OUTSIDE",
    )
