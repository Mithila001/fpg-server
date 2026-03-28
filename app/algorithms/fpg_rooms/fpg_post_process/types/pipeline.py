from __future__ import annotations

from typing import NotRequired, TypedDict

from .geometry import OpeningPayload, RoomBoundaryPayload
from .processor_outputs import WallUnionResultPayload


class ProcessContextPayload(TypedDict):
    rooms: list[RoomBoundaryPayload]
    openings: list[OpeningPayload]
    tolerance: float
    wall_union: NotRequired[WallUnionResultPayload]
