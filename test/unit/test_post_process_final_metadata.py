from app.algorithms.fpg_rooms.fpg_post_process import run_final_post_process


def test_final_post_process_removes_veranda_and_veranda_outdoor_and_extracts_veranda_metadata() -> None:
    payload = {
        "rooms": [
            {"name": "veranda_1", "type": "veranda", "x": 10, "y": 0, "x_end": 50, "y_end": 20},
            {"name": "verandaOutdoorSpace_for_veranda_1", "type": "verandaOutdoorSpace", "x": 50, "y": 0, "x_end": 90, "y_end": 20},
            {"name": "living_1", "type": "livingRoom", "x": 10, "y": 20, "x_end": 60, "y_end": 80},
        ],
        "openings": [],
    }

    result = run_final_post_process(payload)

    assert "veranda_1" not in result["compact_by_room"]
    assert "verandaOutdoorSpace_for_veranda_1" not in result["compact_by_room"]
    assert "living_1" in result["compact_by_room"]

    veranda_metadata = result["metadata"]["veranda"]
    assert veranda_metadata is not None
    assert veranda_metadata["room_name"] == "veranda_1"
    assert veranda_metadata["l_veranda_pillar"] == {"x": 10.0, "y": 0.0}
    assert veranda_metadata["r_veranda_pillar"] == {"x": 50.0, "y": 0.0}
    assert veranda_metadata["veranda_back_points"] == [
        {"x": 10.0, "y": 20.0},
        {"x": 50.0, "y": 20.0},
    ]


def test_final_post_process_detects_garage_veranda_outdoor_horizontal_overlap() -> None:
    payload = {
        "rooms": [
            {"name": "garage_1", "type": "garage", "x": 0, "y": 0, "x_end": 50, "y_end": 20},
            {"name": "verandaOutdoorSpace_for_veranda_1", "type": "verandaOutdoorSpace", "x": 20, "y": 20, "x_end": 80, "y_end": 40},
            {"name": "living_1", "type": "livingRoom", "x": 0, "y": 40, "x_end": 80, "y_end": 90},
        ],
        "openings": [],
    }

    result = run_final_post_process(payload)

    assert result["metadata"]["garage_shared_horizontal_overlap_segment"] == {
        "x1": 20.0,
        "y1": 20.0,
        "x2": 50.0,
        "y2": 20.0,
    }


def test_final_post_process_converts_hallway_living_internal_door_to_cased_door() -> None:
    payload = {
        "rooms": [
            {"name": "hall_1", "type": "hallway", "x": 0, "y": 0, "x_end": 20, "y_end": 50},
            {"name": "living_1", "type": "livingRoom", "x": 20, "y": 0, "x_end": 80, "y_end": 50},
        ],
        "openings": [
            {
                "room_name": "hall_1",
                "room_type": "hallway",
                "opening_type": "internalDoor",
                "x1": 20,
                "y1": 10,
                "x2": 20,
                "y2": 20,
                "connected_room_name": "living_1",
                "connected_room_type": "livingRoom",
            }
        ],
    }

    result = run_final_post_process(payload)

    hall_openings = result["compact_by_room"]["hall_1"]["openings"]
    assert hall_openings[0]["opening_type"] == "casedDoor"
    assert result["metadata"]["converted_hallway_living_openings"] == 1
    assert len(result["metadata"]["hallway_living_shared_walls"]) >= 1
