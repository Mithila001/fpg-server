from __future__ import annotations

from dataclasses import dataclass

from app.algorithms.types.domain import ProcessedRoomData
from app.algorithms.types.openings import OpeningData
from app.core.fpg_opening_config import CARDINAL_SIDES


@dataclass(frozen=True)
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def is_horizontal(self) -> bool:
        return abs(self.y1 - self.y2) < 1e-6

    @property
    def is_vertical(self) -> bool:
        return abs(self.x1 - self.x2) < 1e-6


@dataclass(frozen=True)
class ExteriorSegmentCandidate:
    room: ProcessedRoomData
    segment: Segment
    side: str


def _iter_room_segments(room: ProcessedRoomData) -> list[Segment]:
    vertices = room.vertices
    segments: list[Segment] = []
    for index in range(len(vertices)):
        x1, y1 = vertices[index]
        x2, y2 = vertices[(index + 1) % len(vertices)]
        segments.append(Segment(x1=x1, y1=y1, x2=x2, y2=y2))
    return segments


def _overlap_len_1d(a1: float, a2: float, b1: float, b2: float) -> float:
    start = max(min(a1, a2), min(b1, b2))
    end = min(max(a1, a2), max(b1, b2))
    return max(0.0, end - start)


def _segment_side(room: ProcessedRoomData, segment: Segment, tolerance: float) -> str:
    xs = [point[0] for point in room.vertices]
    ys = [point[1] for point in room.vertices]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if segment.is_horizontal:
        if abs(segment.y1 - min_y) <= tolerance:
            return "south"
        if abs(segment.y1 - max_y) <= tolerance:
            return "north"
    if segment.is_vertical:
        if abs(segment.x1 - min_x) <= tolerance:
            return "west"
        if abs(segment.x1 - max_x) <= tolerance:
            return "east"
    return "unknown"


def _is_exterior_segment(
    room: ProcessedRoomData,
    segment: Segment,
    floor_plan: list[ProcessedRoomData],
    tolerance: float,
) -> bool:
    for other_room in floor_plan:
        if other_room.name == room.name:
            continue
        for other_segment in _iter_room_segments(other_room):
            if segment.is_horizontal and other_segment.is_horizontal:
                if abs(segment.y1 - other_segment.y1) > tolerance:
                    continue
                if (
                    _overlap_len_1d(
                        segment.x1, segment.x2, other_segment.x1, other_segment.x2
                    )
                    > tolerance
                ):
                    return False
            elif segment.is_vertical and other_segment.is_vertical:
                if abs(segment.x1 - other_segment.x1) > tolerance:
                    continue
                if (
                    _overlap_len_1d(
                        segment.y1, segment.y2, other_segment.y1, other_segment.y2
                    )
                    > tolerance
                ):
                    return False
    return True


def build_exterior_segment_candidates(
    floor_plan: list[ProcessedRoomData],
    tolerance: float = 1e-6,
) -> list[ExteriorSegmentCandidate]:
    candidates: list[ExteriorSegmentCandidate] = []
    for room in floor_plan:
        for segment in _iter_room_segments(room):
            if not (segment.is_horizontal or segment.is_vertical):
                continue
            if not _is_exterior_segment(room, segment, floor_plan, tolerance):
                continue
            side = _segment_side(room, segment, tolerance)
            if side in CARDINAL_SIDES:
                candidates.append(
                    ExteriorSegmentCandidate(room=room, segment=segment, side=side)
                )
    return candidates


def select_main_door(
    floor_plan: list[ProcessedRoomData],
    side_priority: tuple[str, ...],
    preferred_door_length: float,
    tolerance: float = 1e-6,
) -> OpeningData | None:
    candidates = build_exterior_segment_candidates(floor_plan, tolerance=tolerance)
    if not candidates:
        return None
    priority = {
        side.strip().lower(): index
        for index, side in enumerate(side_priority)
        if side.strip().lower() in CARDINAL_SIDES
    }
    fallback_start = len(priority)
    for side in CARDINAL_SIDES:
        if side not in priority:
            priority[side] = fallback_start
            fallback_start += 1

    living_room_candidates = [
        c for c in candidates if c.room.type.strip().lower() == "livingroom"
    ]
    ranked_pool = living_room_candidates if living_room_candidates else candidates
    ranked_pool = sorted(
        ranked_pool,
        key=lambda c: (
            priority.get(c.side, 99),
            0 if c.room.type.strip().lower() == "livingroom" else 1,
            c.room.name,
        ),
    )
    selected = ranked_pool[0]
    seg = selected.segment
    if seg.is_horizontal:
        span = abs(seg.x2 - seg.x1)
        if span <= tolerance:
            return None
        door_len = min(preferred_door_length, span)
        mid = (seg.x1 + seg.x2) / 2.0
        x1 = mid - door_len / 2.0
        x2 = mid + door_len / 2.0
        y1 = seg.y1
        y2 = seg.y2
    else:
        span = abs(seg.y2 - seg.y1)
        if span <= tolerance:
            return None
        door_len = min(preferred_door_length, span)
        mid = (seg.y1 + seg.y2) / 2.0
        y1 = mid - door_len / 2.0
        y2 = mid + door_len / 2.0
        x1 = seg.x1
        x2 = seg.x2

    return OpeningData(
        room_name=selected.room.name,
        room_type=selected.room.type,
        opening_type="mainDoor",
        side=selected.side,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        connected_room_name="OUTSIDE",
        connected_room_type="OUTSIDE",
    )
