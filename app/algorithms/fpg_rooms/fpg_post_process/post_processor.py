from __future__ import annotations

from .processors import build_compact_data, run_wall_union
from .types import (
    OpeningPayload,
    PostProcessInputPayload,
    PostProcessMetadataPayload,
    PostProcessOutputPayload,
    ProcessContextPayload,
    QuickPostProcessOutputPayload,
    RoomBoundaryPayload,
    VerandaMetadataPayload,
    WallSegmentPayload,
)
from .utils import normalize_openings, normalize_rooms


def _normalize_room_type(room_type: str) -> str:
    return "".join(ch for ch in room_type.lower() if ch.isalnum())


def _shared_wall_segments(
    room_a: RoomBoundaryPayload,
    room_b: RoomBoundaryPayload,
    tolerance: float,
) -> list[WallSegmentPayload]:
    segments: list[WallSegmentPayload] = []

    if abs(room_a["x_end"] - room_b["x"]) <= tolerance:
        y1 = max(room_a["y"], room_b["y"])
        y2 = min(room_a["y_end"], room_b["y_end"])
        if y2 - y1 > tolerance:
            segments.append({"x1": room_a["x_end"], "y1": y1, "x2": room_a["x_end"], "y2": y2})

    if abs(room_b["x_end"] - room_a["x"]) <= tolerance:
        y1 = max(room_a["y"], room_b["y"])
        y2 = min(room_a["y_end"], room_b["y_end"])
        if y2 - y1 > tolerance:
            segments.append({"x1": room_a["x"], "y1": y1, "x2": room_a["x"], "y2": y2})

    if abs(room_a["y_end"] - room_b["y"]) <= tolerance:
        x1 = max(room_a["x"], room_b["x"])
        x2 = min(room_a["x_end"], room_b["x_end"])
        if x2 - x1 > tolerance:
            segments.append({"x1": x1, "y1": room_a["y_end"], "x2": x2, "y2": room_a["y_end"]})

    if abs(room_b["y_end"] - room_a["y"]) <= tolerance:
        x1 = max(room_a["x"], room_b["x"])
        x2 = min(room_a["x_end"], room_b["x_end"])
        if x2 - x1 > tolerance:
            segments.append({"x1": x1, "y1": room_a["y"], "x2": x2, "y2": room_a["y"]})

    return segments


def _opening_on_shared_segment(
    opening: OpeningPayload,
    segment: WallSegmentPayload,
    tolerance: float,
) -> bool:
    x1 = opening.get("x1")
    y1 = opening.get("y1")
    x2 = opening.get("x2")
    y2 = opening.get("y2")

    if None in (x1, y1, x2, y2):
        return False

    if abs(segment["y1"] - segment["y2"]) <= tolerance:
        segment_y = segment["y1"]
        if abs(float(y1) - segment_y) > tolerance or abs(float(y2) - segment_y) > tolerance:
            return False
        opening_min_x = min(float(x1), float(x2))
        opening_max_x = max(float(x1), float(x2))
        segment_min_x = min(segment["x1"], segment["x2"])
        segment_max_x = max(segment["x1"], segment["x2"])
        return min(opening_max_x, segment_max_x) - max(opening_min_x, segment_min_x) > tolerance

    segment_x = segment["x1"]
    if abs(float(x1) - segment_x) > tolerance or abs(float(x2) - segment_x) > tolerance:
        return False
    opening_min_y = min(float(y1), float(y2))
    opening_max_y = max(float(y1), float(y2))
    segment_min_y = min(segment["y1"], segment["y2"])
    segment_max_y = max(segment["y1"], segment["y2"])
    return min(opening_max_y, segment_max_y) - max(opening_min_y, segment_min_y) > tolerance


def _build_veranda_metadata(room: RoomBoundaryPayload) -> VerandaMetadataPayload:
    left_front = {"x": room["x"], "y": room["y"]}
    right_front = {"x": room["x_end"], "y": room["y"]}
    back_points = [
        {"x": room["x"], "y": room["y_end"]},
        {"x": room["x_end"], "y": room["y_end"]},
    ]
    return {
        "room_name": room["name"],
        "l_veranda_pillar": left_front,
        "r_veranda_pillar": right_front,
        "veranda_back_points": back_points,
    }


def _find_garage_horizontal_overlap_segment(
    rooms: list[RoomBoundaryPayload],
    tolerance: float,
) -> WallSegmentPayload | None:
    garages = [room for room in rooms if _normalize_room_type(room["type"]) == "garage"]
    verandas_outdoor = [
        room for room in rooms if _normalize_room_type(room["type"]) == "verandaoutdoorspace"
    ]

    best_segment: WallSegmentPayload | None = None
    best_length = 0.0

    for garage in garages:
        for veranda_outdoor in verandas_outdoor:
            candidate_y: float | None = None
            if abs(garage["y_end"] - veranda_outdoor["y"]) <= tolerance:
                candidate_y = garage["y_end"]
            elif abs(veranda_outdoor["y_end"] - garage["y"]) <= tolerance:
                candidate_y = garage["y"]

            if candidate_y is None:
                continue

            overlap_x1 = max(garage["x"], veranda_outdoor["x"])
            overlap_x2 = min(garage["x_end"], veranda_outdoor["x_end"])
            overlap_len = overlap_x2 - overlap_x1
            if overlap_len <= tolerance:
                continue

            if overlap_len > best_length:
                best_length = overlap_len
                best_segment = {
                    "x1": overlap_x1,
                    "y1": candidate_y,
                    "x2": overlap_x2,
                    "y2": candidate_y,
                }

    return best_segment


def _convert_hallway_living_openings(
    rooms: list[RoomBoundaryPayload],
    openings: list[OpeningPayload],
    tolerance: float,
) -> tuple[list[OpeningPayload], list[WallSegmentPayload], int]:
    room_by_name = {room["name"]: room for room in rooms}
    hallway_rooms = [room for room in rooms if _normalize_room_type(room["type"]) == "hallway"]
    living_rooms = [room for room in rooms if _normalize_room_type(room["type"]) == "livingroom"]

    shared_segments: list[WallSegmentPayload] = []
    for hallway in hallway_rooms:
        for living_room in living_rooms:
            shared_segments.extend(_shared_wall_segments(hallway, living_room, tolerance))

    updated_openings: list[OpeningPayload] = [dict(opening) for opening in openings]
    converted_count = 0

    for opening in updated_openings:
        opening_type = _normalize_room_type(str(opening.get("opening_type") or ""))
        if opening_type != "internaldoor":
            continue

        room_name = str(opening.get("room_name") or "")
        connected_room_name = str(opening.get("connected_room_name") or "")
        if not room_name or not connected_room_name:
            continue

        room_type = str(opening.get("room_type") or room_by_name.get(room_name, {}).get("type", ""))
        connected_room_type = str(
            opening.get("connected_room_type") or room_by_name.get(connected_room_name, {}).get("type", "")
        )

        normalized_pair = {
            _normalize_room_type(room_type),
            _normalize_room_type(connected_room_type),
        }
        if normalized_pair != {"hallway", "livingroom"}:
            continue

        if not any(_opening_on_shared_segment(opening, segment, tolerance) for segment in shared_segments):
            continue

        opening["opening_type"] = "casedDoor"
        converted_count += 1

    return updated_openings, shared_segments, converted_count


def run_final_post_process(payload: PostProcessInputPayload) -> PostProcessOutputPayload:
    """Heavy Post processor for finalize the data"""
    context: ProcessContextPayload = {
        "rooms": normalize_rooms(payload.get("rooms", [])),
        "openings": normalize_openings(payload.get("openings", [])),
        "tolerance": float(payload.get("tolerance", 1e-6)),
        "wall_union": payload.get("wall_union"),
    }

    first_veranda = next(
        (room for room in context["rooms"] if _normalize_room_type(room["type"]) == "veranda"),
        None,
    )
    filtered_rooms = [
        room
        for room in context["rooms"]
        if _normalize_room_type(room["type"]) not in {"veranda", "verandaoutdoorspace"}
    ]
    wall_union_result = run_wall_union(
        rooms=filtered_rooms,
        tolerance=context["tolerance"],
    )

    updated_openings, hallway_living_shared_walls, converted_hallway_living_openings = _convert_hallway_living_openings(
        rooms=context["rooms"],
        openings=context["openings"],
        tolerance=context["tolerance"],
    )
    filtered_room_names = {room["name"] for room in filtered_rooms}
    filtered_openings = [
        opening for opening in updated_openings if opening.get("room_name") in filtered_room_names
    ]

    metadata: PostProcessMetadataPayload = {
        "veranda": _build_veranda_metadata(first_veranda) if first_veranda is not None else None,
        "garage_shared_horizontal_overlap_segment": _find_garage_horizontal_overlap_segment(
            rooms=context["rooms"],
            tolerance=context["tolerance"],
        ),
        "hallway_living_shared_walls": hallway_living_shared_walls,
        "converted_hallway_living_openings": converted_hallway_living_openings,
    }

    compact_by_room = build_compact_data(
        wall_union=wall_union_result,
        openings=filtered_openings,
        rooms=filtered_rooms,
    )

    return {
        "status": "SUCCESS",
        "message": "Post-processing pipeline completed",
        "walls": wall_union_result["walls"],
        "compact_by_room": compact_by_room,
        "metadata": metadata,
    }


def run_quick_post_process(payload: PostProcessInputPayload) -> QuickPostProcessOutputPayload:
    """Post Process function for iterative post processing for algorithms"""
    context: ProcessContextPayload = {
        "rooms": normalize_rooms(payload.get("rooms", [])),
        "openings": [],
        "tolerance": float(payload.get("tolerance", 1e-6)),
    }

    #snapped_rooms = snap_solution_rooms_to_grid(context["rooms"], grid_size=8.0)

    wall_union_result = run_wall_union(
        rooms=context["rooms"],
        tolerance=context["tolerance"],
    )

    return {
        "status": "SUCCESS",
        "message": "Quick post-processing completed",
        "rooms": context["rooms"],
        "wall_union": wall_union_result,
    }

