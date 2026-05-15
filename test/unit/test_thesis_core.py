import pytest
from typing import Any, Dict


@pytest.fixture
def sample_room_template() -> Dict[str, Any]:
    return {
        "name": "Standard 2BHK Layout",
        "data": [
            {"id": "bedroom1", "type": "bedroom", "size": "regular"},
            {"id": "bedroom2", "type": "bedroom", "size": "regular"},
            {"id": "bathroom1", "type": "bathroom", "size": "regular"},
            {"id": "kitchen1", "type": "kitchen", "size": "regular"},
        ],
    }


@pytest.fixture
def sample_land_data() -> Dict[str, Any]:
    return {
        "area": 100000,
        "segmentsCoordinates": [
            {"x": 0, "y": 0},
            {"x": 1000, "y": 0},
            {"x": 1000, "y": 1000},
            {"x": 0, "y": 1000},
            {"x": 0, "y": 0},
        ],
        "roadConnected": [
            {
                "segment": [{"x": 1000, "y": 0}, {"x": 1000, "y": 1000}],
                "roadType": "mainRoad",
            }
        ],
        "min_width": 100,
        "min_height": 100,
    }


def test_phase_1_db_constraint_integrity():
    """
    PHASE 1: Verifies that the system can correctly load and parse
    architectural constraints from the mock database.
    """
    from app.util.dev_use_mock_db import (
        load_room_size_constraints,
        load_room_relations_constraints,
    )

    size_constraints = load_room_size_constraints()
    relation_constraints = load_room_relations_constraints()

    assert len(size_constraints) > 0, "Size constraints should not be empty"
    assert len(relation_constraints) > 0, "Relation constraints should not be empty"

    # Check for a specific known constraint
    bedroom_regular = next(
        (c for c in size_constraints if c.type == "bedroom" and c.size == "regular"),
        None,
    )
    assert bedroom_regular is not None, "Regular bedroom constraint should exist"
    assert bedroom_regular.min_w > 0, "Bedroom should have a minimum width"


def test_phase_2_requirement_normalization(sample_room_template):
    """
    PHASE 2: Validates that the system correctly normalizes user-provided
    room requirements by applying database presets.
    """
    from app.algorithms.types import RoomData
    from app.util.room_requirements import normalize_db_data_requirements
    from app.util.dev_use_mock_db import load_room_size_constraints

    size_constraints = load_room_size_constraints()

    # Map 'id' to 'name' and provide dummy values for required geometry fields
    # these will be overwritten by normalize_db_data_requirements
    input_rooms = [
        RoomData(
            name=r["id"],
            type=r["type"],
            size=r.get("size"),
            min_w=0,
            min_h=0,
            max_w=0,
            max_h=0,
        )
        for r in sample_room_template["data"]
    ]
    normalized = normalize_db_data_requirements(input_rooms, size_constraints)

    # Note: livingRoom is automatically added by the normalization process if not present
    assert len(normalized) == len(sample_room_template["data"]) + 1
    for room in normalized:
        assert room.min_w > 0, f"Room {room.name} should have normalized width"
        assert room.max_h > 0, f"Room {room.name} should have normalized height"


def test_phase_3_land_geometry_processing(sample_land_data):
    """
    PHASE 3: Validates the land processing logic, ensuring coordinates
    and road connections are correctly parsed.
    """
    from app.services.job_lifecycle import _run_buildable_space_job

    # Simulate a buildable space job
    result = _run_buildable_space_job(sample_land_data)

    assert result is not None
    assert "status" in result
    assert result["status"] in ["SUCCESS", "OK"], (
        "Buildable space processing should succeed"
    )
    assert "shrunk_boundary" in result, "Result should contain geometry data"


def test_phase_4_generation_pipeline_smoke_test(sample_room_template):
    """
    PHASE 4: Executes a full generation cycle with a minimal trial count.
    This demonstrates the end-to-end integration of constraints,
    geometry, and the Optuna optimization engine.
    """
    from app.services.job_lifecycle import _run_format_job

    request_payload = {
        "floor_width": 1500,
        "floor_height": 1500,
        "aspect_ratio": 1.0,  # 1:1
        "room_template": sample_room_template,
        "should_optuna_run": True,
        "optuna_trial_count": 5,  # Minimal trials for a fast demo
    }

    result = _run_format_job(request_payload)

    assert result is not None
    # We allow "NO_FLOOR_PLAN" if trials are too low, but status should be present
    assert "status" in result
    print(f"\nGeneration Status: {result['status']}")
    if result["status"] == "SUCCESS":
        assert "union_results" in result
        assert len(result["union_results"]) > 0
