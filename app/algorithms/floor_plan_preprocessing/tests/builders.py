import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from app.algorithms.floor_plan_preprocessing import (
    FloorLimits,
    PreprocessingInput,
    PreprocessingRequest,
    RequestedRoom,
    RoomRelationReference,
    RoomSizeReference,
)
from app.core_config import load_fpg_core_config
from app.algorithms.types_new import RoomType

DATA_DIR = Path(__file__).parent / "data"


def _load_json(filename: str) -> dict[str, Any]:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def build_preprocessing_input() -> PreprocessingInput:
    request_data = _load_json("valid_request.json")
    reference_data = _load_json("valid_reference_data.json")

    request = PreprocessingRequest(
        floor_limits=FloorLimits(**request_data["floor_limits"]),
        aspect_ratio=request_data["aspect_ratio"],
        rooms=tuple(
            RequestedRoom(
                **{**room, "room_type": RoomType(room["room_type"])}
            )
            for room in request_data["rooms"]
        ),
    )

    base_config = load_fpg_core_config().preprocessing
    config = replace(
        base_config,
        room_sizes=tuple(
            RoomSizeReference(
                **{**room, "room_type": RoomType(room["room_type"])}
            )
            for room in reference_data["room_sizes"]
        ),
        room_relations=tuple(
            RoomRelationReference(
                source_room_type=RoomType(relation["source_room_type"]),
                target_room_types=tuple(
                    RoomType(value) for value in relation["target_room_types"]
                ),
                match_policy=relation["match_policy"],
                strength=relation["strength"],
                required=relation.get("required", True),
            )
            for relation in reference_data["room_relations"]
        ),
    )

    return PreprocessingInput(request=request, config=config)
