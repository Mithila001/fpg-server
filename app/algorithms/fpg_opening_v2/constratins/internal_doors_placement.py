from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.algorithms.types.domain import ProcessedRoomData
from app.algorithms.types.openings import OpeningData
from app.core.fpg_opening_config import (
    INTERNAL_DOOR_ALLOWED_ROOM_PAIRS,
    MAX_INTERNAL_DOORS_BY_ROOM_TYPE,
    normalize_room_type,
)


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
class InternalDoorCandidate:
    room_a: ProcessedRoomData
    room_b: ProcessedRoomData
    segment: Segment
    side_a: str
    side_b: str


def _iter_room_segments(room: ProcessedRoomData) -> list[Segment]:
    vertices = room.vertices
    if len(vertices) < 2:
        return []
    segments: list[Segment] = []
    for index in range(len(vertices)):
        x1, y1 = vertices[index]
        x2, y2 = vertices[(index + 1) % len(vertices)]
        segments.append(Segment(x1=x1, y1=y1, x2=x2, y2=y2))
    return segments


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


def _overlap_1d(
    a1: float, a2: float, b1: float, b2: float
) -> tuple[float, float] | None:
    start = max(min(a1, a2), min(b1, b2))
    end = min(max(a1, a2), max(b1, b2))
    if end <= start:
        return None
    return start, end


def _is_allowed_connection(room_type_a: str, room_type_b: str) -> bool:
    a = normalize_room_type(room_type_a)
    b = normalize_room_type(room_type_b)
    if a == "attachedbathroom" or b == "attachedbathroom":
        return frozenset((a, b)) == frozenset(("bedroom", "attachedbathroom"))
    if a == "hallway" or b == "hallway":
        return True
    return frozenset((a, b)) in INTERNAL_DOOR_ALLOWED_ROOM_PAIRS


# TODO: min shared length need to be centralized
def build_internal_door_candidates(
    floor_plan: list[ProcessedRoomData],
    tolerance: float = 1e-6,
    min_shared_length: float = 10,
) -> list[InternalDoorCandidate]:
    candidates: list[InternalDoorCandidate] = []
    for room_a_index, room_a in enumerate(floor_plan):
        segments_a = _iter_room_segments(room_a)
        for room_b in floor_plan[room_a_index + 1 :]:
            if not _is_allowed_connection(room_a.type, room_b.type):
                continue
            segments_b = _iter_room_segments(room_b)
            for segment_a in segments_a:
                for segment_b in segments_b:
                    if segment_a.is_horizontal and segment_b.is_horizontal:
                        if abs(segment_a.y1 - segment_b.y1) > tolerance:
                            continue
                        overlap = _overlap_1d(
                            segment_a.x1, segment_a.x2, segment_b.x1, segment_b.x2
                        )
                        if (
                            overlap is None
                            or overlap[1] - overlap[0] < min_shared_length
                        ):
                            continue
                        candidates.append(
                            InternalDoorCandidate(
                                room_a=room_a,
                                room_b=room_b,
                                segment=Segment(
                                    x1=overlap[0],
                                    y1=segment_a.y1,
                                    x2=overlap[1],
                                    y2=segment_a.y1,
                                ),
                                side_a=_segment_side(room_a, segment_a, tolerance),
                                side_b=_segment_side(room_b, segment_b, tolerance),
                            )
                        )
                    elif segment_a.is_vertical and segment_b.is_vertical:
                        if abs(segment_a.x1 - segment_b.x1) > tolerance:
                            continue
                        overlap = _overlap_1d(
                            segment_a.y1, segment_a.y2, segment_b.y1, segment_b.y2
                        )
                        if (
                            overlap is None
                            or overlap[1] - overlap[0] < min_shared_length
                        ):
                            continue
                        candidates.append(
                            InternalDoorCandidate(
                                room_a=room_a,
                                room_b=room_b,
                                segment=Segment(
                                    x1=segment_a.x1,
                                    y1=overlap[0],
                                    x2=segment_a.x1,
                                    y2=overlap[1],
                                ),
                                side_a=_segment_side(room_a, segment_a, tolerance),
                                side_b=_segment_side(room_b, segment_b, tolerance),
                            )
                        )
    return candidates


def select_internal_doors(
    candidates: list[InternalDoorCandidate],
    preferred_door_length: float,
    tolerance: float = 1e-6,
) -> list[OpeningData]:
    room_incident_count: defaultdict[str, int] = defaultdict(int)
    selected: list[OpeningData] = []
    if not candidates:
        return selected

    # Step 1: Detect bedrooms with attached bathrooms from candidates
    bedrooms_with_attached_bathrooms: set[str] = set()
    for candidate in candidates:
        room_a_type = normalize_room_type(candidate.room_a.type)
        room_b_type = normalize_room_type(candidate.room_b.type)

        # Check if this is a bedroom-attachedBathroom connection
        if room_a_type == "bedroom" and room_b_type == "attachedbathroom":
            bedrooms_with_attached_bathrooms.add(candidate.room_a.name)
        elif room_b_type == "bedroom" and room_a_type == "attachedbathroom":
            bedrooms_with_attached_bathrooms.add(candidate.room_b.name)

    # Step 2: Separate candidates by priority
    # Bathroom-hallway doors get highest priority (soft preference),
    # then other bathroom doors, then social doors
    bathroom_hallway_candidates: list[InternalDoorCandidate] = []
    preferred_hallway_candidates: list[InternalDoorCandidate] = []
    other_bathroom_candidates: list[InternalDoorCandidate] = []
    social_candidates: list[InternalDoorCandidate] = []

    preferred_room_types = {"bedroom", "kitchen", "bathroom", "garage"}
    room_hallway_livingroom_connections: defaultdict[str, set[str]] = defaultdict(set)
    for candidate in candidates:
        room_a_type = normalize_room_type(candidate.room_a.type)
        room_b_type = normalize_room_type(candidate.room_b.type)

        if room_a_type in preferred_room_types and room_b_type in {
            "hallway",
            "livingroom",
        }:
            room_hallway_livingroom_connections[candidate.room_a.name].add(room_b_type)
        if room_b_type in preferred_room_types and room_a_type in {
            "hallway",
            "livingroom",
        }:
            room_hallway_livingroom_connections[candidate.room_b.name].add(room_a_type)

    rooms_with_hallway_and_livingroom = {
        room_name
        for room_name, connected_types in room_hallway_livingroom_connections.items()
        if {"hallway", "livingroom"}.issubset(connected_types)
    }

    def _is_preferred_hallway_candidate(
        candidate: InternalDoorCandidate,
    ) -> bool:
        room_a_type = normalize_room_type(candidate.room_a.type)
        room_b_type = normalize_room_type(candidate.room_b.type)

        if (
            room_a_type in preferred_room_types
            and room_b_type == "hallway"
            and candidate.room_a.name in rooms_with_hallway_and_livingroom
        ):
            return True
        if (
            room_b_type in preferred_room_types
            and room_a_type == "hallway"
            and candidate.room_b.name in rooms_with_hallway_and_livingroom
        ):
            return True
        return False

    for candidate in candidates:
        room_a_type = normalize_room_type(candidate.room_a.type)
        room_b_type = normalize_room_type(candidate.room_b.type)

        # Identify bathroom-hallway or hallway-bathroom connections
        if (room_a_type == "bathroom" and room_b_type == "hallway") or (
            room_b_type == "bathroom" and room_a_type == "hallway"
        ):
            bathroom_hallway_candidates.append(candidate)
        elif _is_preferred_hallway_candidate(candidate):
            preferred_hallway_candidates.append(candidate)
        # Other bathroom connections (bathroom-livingroom, etc)
        elif room_a_type == "bathroom" or room_b_type == "bathroom":
            other_bathroom_candidates.append(candidate)
        # Social doors (bedroom-hallway, bedroom-livingroom, etc)
        else:
            social_candidates.append(candidate)

    # Step 3: Process candidates in priority order: bathroom-hallway > preferred hallway > other bathroom > social
    all_candidates_ordered = (
        bathroom_hallway_candidates
        + preferred_hallway_candidates
        + other_bathroom_candidates
        + social_candidates
    )

    for candidate in all_candidates_ordered:
        room_a_type = normalize_room_type(candidate.room_a.type)
        room_b_type = normalize_room_type(candidate.room_b.type)

        # Determine max doors based on dynamic limits for bedrooms
        if room_a_type == "bedroom":
            # Bedroom without attached bathroom: max 1 door
            # Bedroom with attached bathroom: max 2 doors (1 social + 1 bathroom)
            room_a_max = (
                2 if candidate.room_a.name in bedrooms_with_attached_bathrooms else 1
            )
        else:
            room_a_max = MAX_INTERNAL_DOORS_BY_ROOM_TYPE.get(room_a_type, 10)

        if room_b_type == "bedroom":
            room_b_max = (
                2 if candidate.room_b.name in bedrooms_with_attached_bathrooms else 1
            )
        else:
            room_b_max = MAX_INTERNAL_DOORS_BY_ROOM_TYPE.get(room_b_type, 10)

        if room_incident_count[candidate.room_a.name] >= room_a_max:
            continue
        if room_incident_count[candidate.room_b.name] >= room_b_max:
            continue

        seg = candidate.segment
        if seg.is_horizontal:
            span = abs(seg.x2 - seg.x1)
            if span <= tolerance:
                continue
            door_len = min(preferred_door_length, span)
            mid = (seg.x1 + seg.x2) / 2.0
            x1 = mid - door_len / 2.0
            x2 = mid + door_len / 2.0
            y1 = seg.y1
            y2 = seg.y2
        else:
            span = abs(seg.y2 - seg.y1)
            if span <= tolerance:
                continue
            door_len = min(preferred_door_length, span)
            mid = (seg.y1 + seg.y2) / 2.0
            y1 = mid - door_len / 2.0
            y2 = mid + door_len / 2.0
            x1 = seg.x1
            x2 = seg.x2

        selected.append(
            OpeningData(
                room_name=candidate.room_a.name,
                room_type=candidate.room_a.type,
                opening_type="internalDoor",
                side=candidate.side_a,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                connected_room_name=candidate.room_b.name,
                connected_room_type=candidate.room_b.type,
            )
        )
        room_incident_count[candidate.room_a.name] += 1
        room_incident_count[candidate.room_b.name] += 1

    return selected
