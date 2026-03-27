from __future__ import annotations

from typing import Any

from ..types import OpeningPayload, RoomBoundaryPayload


def normalize_rooms(rooms: list[dict[str, Any]]) -> list[RoomBoundaryPayload]:
    """Normalize room payloads into strict room boundary records."""
    normalized: list[RoomBoundaryPayload] = []

    for idx, room in enumerate(rooms):
        try:
            x = float(room["x"])
            y = float(room["y"])

            w = room.get("w")
            h = room.get("h")
            x_end = room.get("x_end")
            y_end = room.get("y_end")

            if x_end is None:
                if w is None:
                    continue
                x_end = x + float(w)
            else:
                x_end = float(x_end)

            if y_end is None:
                if h is None:
                    continue
                y_end = y + float(h)
            else:
                y_end = float(y_end)

            if x_end <= x or y_end <= y:
                continue

            normalized.append(
                {
                    "name": str(room.get("name") or f"room_{idx}"),
                    "type": str(room.get("type") or ""),
                    "x": x,
                    "y": y,
                    "x_end": x_end,
                    "y_end": y_end,
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    return normalized


def normalize_openings(openings: list[dict[str, Any]]) -> list[OpeningPayload]:
    """Normalize opening payloads with required room_name and optional geometry fields."""
    normalized: list[OpeningPayload] = []

    for opening in openings:
        room_name = opening.get("room_name")
        if not room_name:
            continue

        normalized_opening: OpeningPayload = {
            "room_name": str(room_name),
        }

        for key in (
            "room_type",
            "opening_type",
            "side",
            "connected_room_name",
            "connected_room_type",
        ):
            if key in opening and opening[key] is not None:
                normalized_opening[key] = str(opening[key])

        for key in ("x1", "y1", "x2", "y2"):
            if key in opening and opening[key] is not None:
                try:
                    normalized_opening[key] = float(opening[key])
                except (TypeError, ValueError):
                    continue

        normalized.append(normalized_opening)

    return normalized
