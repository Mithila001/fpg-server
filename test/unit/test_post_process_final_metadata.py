from app.algorithms.fpg_rooms.fpg_post_process import run_final_post_process


def test_final_post_process_filters_verandaoutdoorspace_and_returns_room_payloads() -> None:
    payload = {
        "rooms": [
            {"name": "veranda_1", "type": "veranda", "x": 10, "y": 0, "x_end": 50, "y_end": 20},
            {"name": "verandaOutdoorSpace_for_veranda_1", "type": "verandaOutdoorSpace", "x": 50, "y": 0, "x_end": 90, "y_end": 20},
            {"name": "living_1", "type": "livingRoom", "x": 10, "y": 20, "x_end": 60, "y_end": 80},
        ],
        "openings": [],
    }

    result = run_final_post_process(payload)

    assert "veranda_1" in result["rooms"]
    assert "verandaOutdoorSpace_for_veranda_1" not in result["rooms"]
    assert "living_1" in result["rooms"]
    assert result["rooms"]["living_1"]["room_type"] == "livingRoom"
    assert isinstance(result["union_walls"], list)
    assert isinstance(result["rooms"]["veranda_1"]["room_walls"], list)


def test_final_post_process_classifies_openings_into_doors_and_windows() -> None:
    payload = {
        "rooms": [
            {"name": "bedroom_1", "type": "bedroom", "x": 0, "y": 0, "x_end": 50, "y_end": 50},
            {"name": "living_1", "type": "livingRoom", "x": 50, "y": 0, "x_end": 100, "y_end": 50},
        ],
        "openings": [
            {
                "room_name": "bedroom_1",
                "room_type": "bedroom",
                "opening_type": "window",
                "x1": 10,
                "y1": 50,
                "x2": 20,
                "y2": 50,
            },
            {
                "room_name": "bedroom_1",
                "room_type": "bedroom",
                "opening_type": "internalDoor",
                "x1": 50,
                "y1": 20,
                "x2": 50,
                "y2": 30,
                "connected_room_name": "living_1",
                "connected_room_type": "livingRoom",
            },
        ],
    }

    result = run_final_post_process(payload)

    assert len(result["windows"]) == 1
    assert result["windows"][0]["opening_type"] == "default_window"
    assert len(result["doors"]) == 1
    assert result["doors"][0]["room1_name"] == "bedroom_1"
    assert result["doors"][0]["room2_name"] == "living_1"


def test_final_post_process_filters_openings_linked_to_verandaoutdoorspace() -> None:
    payload = {
        "rooms": [
            {"name": "living_1", "type": "livingRoom", "x": 0, "y": 0, "x_end": 50, "y_end": 50},
            {"name": "verandaOutdoorSpace_for_veranda_1", "type": "verandaOutdoorSpace", "x": 50, "y": 0, "x_end": 90, "y_end": 20},
        ],
        "openings": [
            {
                "room_name": "living_1",
                "room_type": "livingRoom",
                "opening_type": "internalDoor",
                "x1": 50,
                "y1": 10,
                "x2": 50,
                "y2": 20,
                "connected_room_name": "verandaOutdoorSpace_for_veranda_1",
                "connected_room_type": "verandaOutdoorSpace",
            }
        ],
    }

    result = run_final_post_process(payload)

    assert result["doors"] == []
    assert result["windows"] == []
