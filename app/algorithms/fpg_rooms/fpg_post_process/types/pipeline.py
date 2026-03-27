from __future__ import annotations

from typing import TypedDict

from .geometry import OpeningPayload, RoomBoundaryPayload


class ProcessContextPayload(TypedDict):
    rooms: list[RoomBoundaryPayload]
    openings: list[OpeningPayload]
    tolerance: float
