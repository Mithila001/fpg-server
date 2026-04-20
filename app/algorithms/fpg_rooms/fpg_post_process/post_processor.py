from __future__ import annotations

from typing import Any

from .processors import run_wall_union
from .types import (
    OpeningPayload,
    PostProcessInputPayload,
    PostProcessOutputPayload,
    ProcessContextPayload,
    QuickPostProcessOutputPayload,
    RoomBoundaryPayload,
    RoomWallsPayload,
    WallSegmentPayload,
)
from .utils import normalize_openings, normalize_rooms


def _normalize_room_type(room_type: str) -> str:
    return "".join(ch for ch in room_type.lower() if ch.isalnum())


def _filter_rooms(rooms: list[RoomBoundaryPayload]) -> list[RoomBoundaryPayload]:
    return [
        room for room in rooms if _normalize_room_type(room["type"]) != "verandaoutdoorspace"
    ]


def _filter_openings(openings: list[OpeningPayload], rooms: list[RoomBoundaryPayload]) -> list[OpeningPayload]:
    veranda_outdoor_room_names = {
        room["name"] for room in rooms if _normalize_room_type(room["type"]) == "verandaoutdoorspace"
    }
    filtered: list[OpeningPayload] = []
    for opening in openings:
        room_name = str(opening.get("room_name") or "")
        connected_room_name = str(opening.get("connected_room_name") or "")
        if room_name in veranda_outdoor_room_names or connected_room_name in veranda_outdoor_room_names:
            continue

        room_type = str(opening.get("room_type") or "")
        connected_room_type = str(opening.get("connected_room_type") or "")
        if _normalize_room_type(room_type) == "verandaoutdoorspace":
            continue
        if _normalize_room_type(connected_room_type) == "verandaoutdoorspace":
            continue
        filtered.append(opening)
    return filtered


def _build_room_outputs(room_walls: dict[str, RoomWallsPayload]) -> dict[str, dict[str, Any]]:
    return {
        room_name: {
            "room_name": room_name,
            "room_type": room_payload["room_type"],
            "room_walls": room_payload["walls"],
        }
        for room_name, room_payload in room_walls.items()
    }


def _build_doors_and_windows(
    openings: list[OpeningPayload],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    doors: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []

    for opening in openings:
        opening_type = str(opening.get("opening_type") or "").strip()
        normalized_type = _normalize_room_type(opening_type)

        if normalized_type == "window":
            windows.append(
                {
                    "room_name": opening["room_name"],
                    "room_type": opening.get("room_type", ""),
                    "opening_type": "default_window",
                    "x1": opening.get("x1"),
                    "y1": opening.get("y1"),
                    "x2": opening.get("x2"),
                    "y2": opening.get("y2"),
                }
            )
            continue

        doors.append(
            {
                "room1_name": opening["room_name"],
                "room1_type": opening.get("room_type", ""),
                "room2_name": opening.get("connected_room_name", ""),
                "room2_type": opening.get("connected_room_type", ""),
                "opening_type": opening_type or "",
                "x1": opening.get("x1"),
                "y1": opening.get("y1"),
                "x2": opening.get("x2"),
                "y2": opening.get("y2"),
            }
        )

    return doors, windows


def run_final_post_process(payload: PostProcessInputPayload) -> PostProcessOutputPayload:
    """Heavy post processor for final layout payload shape."""
    context: ProcessContextPayload = {
        "rooms": normalize_rooms(payload.get("rooms", [])),
        "openings": normalize_openings(payload.get("openings", [])),
        "tolerance": float(payload.get("tolerance", 1e-6)),
    }

    filtered_rooms = _filter_rooms(context["rooms"])
    filtered_openings = _filter_openings(context["openings"], context["rooms"])

    wall_union_result = run_wall_union(
        rooms=filtered_rooms,
        tolerance=context["tolerance"],
    )

    doors, windows = _build_doors_and_windows(filtered_openings)
    return {
        "status": "SUCCESS",
        "message": "Post-processing pipeline completed",
        "union_walls": wall_union_result["walls"],
        "rooms": _build_room_outputs(wall_union_result["room_walls"]),
        "doors": doors,
        "windows": windows,
    }


def run_quick_post_process(payload: PostProcessInputPayload) -> QuickPostProcessOutputPayload:
    """Post Process function for iterative post processing for algorithms"""
    context: ProcessContextPayload = {
        "rooms": normalize_rooms(payload.get("rooms", [])),
        "openings": [],
        "tolerance": float(payload.get("tolerance", 1e-6)),
    }

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

