from __future__ import annotations

from app.algorithms.fpg_opening_v2.constratins.main_door_to_outside import (
    ExteriorSegmentCandidate,
    build_exterior_segment_candidates,
)
from app.algorithms.types.domain import ProcessedRoomData
from app.algorithms.types.openings import OpeningData
from app.core.fpg_opening_config import WINDOW_ELIGIBLE_ROOM_TYPES, normalize_room_type


def _segment_axis_interval(candidate: ExteriorSegmentCandidate) -> tuple[float, float]:
    segment = candidate.segment
    if abs(segment.y1 - segment.y2) < 1e-6:
        return min(segment.x1, segment.x2), max(segment.x1, segment.x2)
    return min(segment.y1, segment.y2), max(segment.y1, segment.y2)


def _opening_axis_interval(opening: OpeningData) -> tuple[float, float]:
    if opening.side in {"south", "north"}:
        return min(opening.x1, opening.x2), max(opening.x1, opening.x2)
    return min(opening.y1, opening.y2), max(opening.y1, opening.y2)


def _conflicts(
    room_name: str,
    side: str,
    start: float,
    end: float,
    existing_openings: list[OpeningData],
    clearance: float,
    tolerance: float,
) -> bool:
    for opening in existing_openings:
        if opening.room_name != room_name or opening.side != side:
            continue
        other_start, other_end = _opening_axis_interval(opening)
        if start <= other_end + tolerance and other_start <= end + tolerance:
            return True
        gap = min(abs(start - other_end), abs(other_start - end))
        if gap + tolerance < clearance:
            return True
    return False


def select_windows(
    floor_plan: list[ProcessedRoomData],
    existing_openings: list[OpeningData],
    window_width: float,
    window_door_clearance: float,
    tolerance: float = 1e-6,
) -> list[OpeningData]:
    exterior = build_exterior_segment_candidates(floor_plan, tolerance=tolerance)
    by_room: dict[str, list[ExteriorSegmentCandidate]] = {}
    for candidate in exterior:
        by_room.setdefault(candidate.room.name, []).append(candidate)

    selected_windows: list[OpeningData] = []
    for room in floor_plan:
        if normalize_room_type(room.type) not in WINDOW_ELIGIBLE_ROOM_TYPES:
            continue
        candidates = by_room.get(room.name, [])
        if not candidates:
            continue

        ranked = sorted(
            candidates,
            key=lambda c: (0 if c.side in {"north", "east"} else 1, c.side),
        )
        selected_for_room: OpeningData | None = None
        for candidate in ranked:
            start, end = _segment_axis_interval(candidate)
            span = end - start
            if span + tolerance < window_width:
                continue
            width = min(window_width, span)
            mid = (start + end) / 2.0
            axis_start = mid - width / 2.0
            axis_end = mid + width / 2.0
            if _conflicts(
                room_name=room.name,
                side=candidate.side,
                start=axis_start,
                end=axis_end,
                existing_openings=existing_openings + selected_windows,
                clearance=window_door_clearance,
                tolerance=tolerance,
            ):
                continue

            segment = candidate.segment
            if abs(segment.y1 - segment.y2) < 1e-6:
                opening = OpeningData(
                    room_name=room.name,
                    room_type=room.type,
                    opening_type="window",
                    side=candidate.side,
                    x1=axis_start,
                    y1=segment.y1,
                    x2=axis_end,
                    y2=segment.y2,
                    connected_room_name="OUTSIDE",
                    connected_room_type="OUTSIDE",
                )
            else:
                opening = OpeningData(
                    room_name=room.name,
                    room_type=room.type,
                    opening_type="window",
                    side=candidate.side,
                    x1=segment.x1,
                    y1=axis_start,
                    x2=segment.x2,
                    y2=axis_end,
                    connected_room_name="OUTSIDE",
                    connected_room_type="OUTSIDE",
                )
            selected_for_room = opening
            break

        if selected_for_room is not None:
            selected_windows.append(selected_for_room)

    return selected_windows
