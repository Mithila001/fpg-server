from __future__ import annotations

from app.algorithms.types.public import (
    CompactRoomPayload,
    OpeningPayload,
    RoomBoundaryPayload,
    WallUnionResultPayload,
)


def build_compact_data(
    wall_union: WallUnionResultPayload,
    openings: list[OpeningPayload],
    rooms: list[RoomBoundaryPayload],
) -> dict[str, CompactRoomPayload]:
    """Combine room walls and opening payloads into a room_name keyed object."""
    compact_by_room: dict[str, CompactRoomPayload] = {
        room["name"]: {
            "room_name": room["name"],
            "room_type": room["type"],
            "walls": wall_union["room_walls"].get(room["name"], {"walls": []})["walls"],
            "openings": [],
        }
        for room in rooms
    }

    for opening in openings:
        room_name = opening["room_name"]
        if room_name not in compact_by_room:
            compact_by_room[room_name] = {
                "room_name": room_name,
                "room_type": "",
                "walls": [],
                "openings": [],
            }
        compact_by_room[room_name]["openings"].append(opening)

    return compact_by_room
