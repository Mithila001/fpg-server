import json
from pathlib import Path
from typing import Any

from app.algorithms.floor_plan_preprocessing import (
    FloorLimits,
    PreprocessingInput,
    PreprocessingReferenceData,
    PreprocessingRequest,
    RequestedRoom,
    RoomRelationReference,
    RoomSizeReference,
)

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
            RequestedRoom(**room)
            for room in request_data["rooms"]
        ),
    )

    references = PreprocessingReferenceData(
        room_sizes=tuple(
            RoomSizeReference(**room)
            for room in reference_data["room_sizes"]
        ),
        room_relations=tuple(
            RoomRelationReference(
                source_room_type=relation["source_room_type"],
                target_room_types=tuple(
                    relation["target_room_types"]
                ),
                match_policy=relation["match_policy"],
                strength=relation["strength"],
                required=relation.get("required", True),
            )
            for relation in reference_data["room_relations"]
        ),
    )

    return PreprocessingInput(
        request=request,
        reference_data=references,
    )