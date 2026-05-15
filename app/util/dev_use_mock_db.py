import json
from pathlib import Path
from typing import Any, List

from app.types.room_relations_constraint import RoomRelationsConstraint
from app.types.room_setup_template import RoomSetupTemplate
from app.types.room_size_constraint import RoomSizeConstraint


REPO_ROOT = Path(__file__).resolve().parents[2]
MOCK_DATA_DIR = REPO_ROOT / "test" / "db-mock"


def _load_json(file_name: str) -> Any:
    file_path = MOCK_DATA_DIR / file_name
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_room_setup_templates() -> List[RoomSetupTemplate]:
    raw = _load_json("room_setup_templates.json")
    return [RoomSetupTemplate(**item) for item in raw]


def load_room_size_constraints() -> List[RoomSizeConstraint]:
    raw = _load_json("room_size_constraints.json")

    if isinstance(raw, list):
        return [RoomSizeConstraint(**item) for item in raw]

    if not isinstance(raw, dict):
        raise ValueError("room_size_constraints.json must be a list or object")

    flattened: list[dict[str, Any]] = []
    for room_type, size_map in raw.items():
        if not isinstance(size_map, dict):
            raise ValueError(
                f"Invalid size mapping for room type '{room_type}': expected object"
            )

        for size_label, preset in size_map.items():
            if not isinstance(preset, dict):
                raise ValueError(
                    f"Invalid preset for room type '{room_type}', size '{size_label}': expected object"
                )

            flattened.append(
                {
                    "type": room_type,
                    "size": size_label,
                    **preset,
                }
            )

    return [RoomSizeConstraint(**item) for item in flattened]


def load_room_relations_constraints() -> List[RoomRelationsConstraint]:
    raw = _load_json("room_relations_constraints.json")
    return [RoomRelationsConstraint(**item) for item in raw]
