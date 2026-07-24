import json

import pytest

from app.algorithms.floor_plan_preprocessing import ReferenceDataError
from app.algorithms.types_new import RoomType
from app.pipeline.generation.context import load_generation_reference_data


def test_reference_loader_rejects_noncanonical_room_type(tmp_path) -> None:
    path = tmp_path / "reference.json"
    path.write_text(
        json.dumps(
            {
                "room_sizes": [
                    {
                        "room_type": "Garage",
                        "size": "regular",
                        "min_width": 10,
                        "max_width": 20,
                        "min_area": 100,
                        "max_area": 400,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReferenceDataError, match="Could not load"):
        load_generation_reference_data(path)


def test_packaged_reference_loader_returns_room_type_enums() -> None:
    reference_data = load_generation_reference_data()

    assert reference_data.room_sizes
    assert all(
        isinstance(reference.room_type, RoomType)
        for reference in reference_data.room_sizes
    )
    assert all(
        isinstance(relation.source_room_type, RoomType)
        and all(isinstance(room_type, RoomType) for room_type in relation.target_room_types)
        for relation in reference_data.room_relations
    )


def test_reference_loader_rejects_legacy_length_fields(tmp_path) -> None:
    path = tmp_path / "reference.json"
    path.write_text(
        json.dumps(
            {
                "room_sizes": [
                    {
                        "room_type": "bedroom",
                        "size": "regular",
                        "min_width": 10,
                        "max_width": 20,
                        "min_length": 10,
                        "max_length": 20,
                        "min_area": 100,
                        "max_area": 400,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReferenceDataError, match="Could not load"):
        load_generation_reference_data(path)
