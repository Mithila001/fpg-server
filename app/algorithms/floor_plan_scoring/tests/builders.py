from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.algorithms.types_new import (
    ConstraintStrength,
    FloorPlan,
    FloorPlanGenerationSpec,
    FloorPlanRoom,
    FloorSpec,
    MatchPolicy,
    Point,
    Polygon,
    RoomId,
    RoomRelationSpec,
    RoomSizeSpec,
    RoomSpec,
    RoomType,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_CASE_FILE = DATA_DIR / "realistic_floor_plan.json"

Coordinate = tuple[int, int]
BoundaryOverrides = Mapping[str, Sequence[Coordinate]]
SizeOverrides = Mapping[str, Mapping[str, int | float]]


def load_case_data(path: Path = DEFAULT_CASE_FILE) -> dict[str, Any]:
    """Load a reusable scoring case without mutating the source JSON."""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_floor_plan(
    *,
    boundary_overrides: BoundaryOverrides | None = None,
    excluded_room_ids: set[str] | None = None,
    data: Mapping[str, Any] | None = None,
) -> FloorPlan:
    """Build a realistic floor plan using the shared types_new contracts."""

    case = deepcopy(dict(data)) if data is not None else load_case_data()
    boundary_overrides = boundary_overrides or {}
    excluded_room_ids = excluded_room_ids or set()

    rooms: list[FloorPlanRoom] = []
    for raw_room in case["rooms"]:
        room_id = str(raw_room["id"])
        if room_id in excluded_room_ids:
            continue

        raw_boundary = boundary_overrides.get(room_id, raw_room["boundary"])
        rooms.append(
            FloorPlanRoom(
                id=RoomId(room_id),
                room_type=RoomType(raw_room["room_type"]),
                name=str(raw_room["name"]),
                boundary=_build_polygon(raw_boundary),
            )
        )

    return FloorPlan(
        boundary=_build_polygon(case["floor"]["boundary"]),
        rooms=rooms,
    )


def build_generation_spec(
    *,
    size_overrides: SizeOverrides | None = None,
    relation_overrides: Sequence[RoomRelationSpec] | None = None,
    data: Mapping[str, Any] | None = None,
) -> FloorPlanGenerationSpec:
    """Build the matching realistic generation specification."""

    case = deepcopy(dict(data)) if data is not None else load_case_data()
    size_overrides = size_overrides or {}

    room_specs: list[RoomSpec] = []
    for raw_room in case["rooms"]:
        room_id = str(raw_room["id"])
        raw_size = dict(raw_room["size"])
        raw_size.update(size_overrides.get(room_id, {}))

        room_specs.append(
            RoomSpec(
                id=RoomId(room_id),
                room_type=RoomType(raw_room["room_type"]),
                name=str(raw_room["name"]),
                size=RoomSizeSpec(
                    min_width=float(raw_size["min_width"]),
                    max_width=float(raw_size["max_width"]),
                    min_height=float(raw_size["min_height"]),
                    max_height=float(raw_size["max_height"]),
                    min_area=float(raw_size["min_area"]),
                    max_area=float(raw_size["max_area"]),
                ),
                required=bool(raw_room.get("required", True)),
            )
        )

    relations = (
        tuple(relation_overrides)
        if relation_overrides is not None
        else tuple(_build_relation(item) for item in case["relations"])
    )

    return FloorPlanGenerationSpec(
        floor=FloorSpec(
            width=float(case["floor"]["width"]),
            height=float(case["floor"]["height"]),
        ),
        rooms=tuple(room_specs),
        room_relations=relations,
    )


def build_realistic_case() -> tuple[FloorPlan, FloorPlanGenerationSpec]:
    """Build the primary real-pipeline scoring input pair."""

    data = load_case_data()
    return build_floor_plan(data=data), build_generation_spec(data=data)


def build_under_minimum_bedroom_spec() -> FloorPlanGenerationSpec:
    """Keep geometry valid while making one bedroom fail its area target."""

    return build_generation_spec(
        size_overrides={
            "bedroom_3": {
                "min_area": 1400,
                "max_area": 1700,
            }
        }
    )


def build_broken_adjacency_spec() -> FloorPlanGenerationSpec:
    """Create a realistic specification containing one unsatisfied hard relation."""

    base = build_generation_spec()
    impossible_relation = RoomRelationSpec(
        source_room_id=RoomId("living_1"),
        target_room_ids=(RoomId("bedroom_3"),),
        match_policy=MatchPolicy.AND,
        strength=ConstraintStrength.HARD,
    )
    return FloorPlanGenerationSpec(
        floor=base.floor,
        rooms=base.rooms,
        room_relations=(*base.room_relations, impossible_relation),
    )


def _build_relation(raw: Mapping[str, Any]) -> RoomRelationSpec:
    return RoomRelationSpec(
        source_room_id=RoomId(str(raw["source_room_id"])),
        target_room_ids=tuple(
            RoomId(str(room_id)) for room_id in raw["target_room_ids"]
        ),
        match_policy=MatchPolicy(str(raw["match_policy"])),
        strength=ConstraintStrength(str(raw["strength"])),
    )


def _build_polygon(raw_points: Sequence[Coordinate]) -> Polygon:
    return Polygon(
        points=tuple(Point(x=int(x), y=int(y)) for x, y in raw_points)
    )
