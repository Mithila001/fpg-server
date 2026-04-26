from __future__ import annotations

from app.algorithms.fpg_opening import generate_openings
from app.algorithms.fpg_opening.constraints.windows_placement import (
    build_window_candidates_for_room,
)
from app.algorithms.types import NormalizedRoom, OpeningPayload


def test_window_rejects_back_door_overlap_or_tight_gap() -> None:
    room: NormalizedRoom = {
        "name": "kitchen1",
        "type": "kitchen",
        "x": 0.0,
        "y": 0.0,
        "x_end": 40.0,
        "y_end": 20.0,
    }
    back_door: OpeningPayload = {
        "room_name": "kitchen1",
        "room_type": "kitchen",
        "opening_type": "backDoor",
        "side": "south",
        "x1": 10.0,
        "y1": 0.0,
        "x2": 18.0,
        "y2": 0.0,
    }

    candidates = build_window_candidates_for_room(
        room=room,
        exterior_sides={"south"},
        existing_openings=[back_door],
        window_width=8.0,
        door_clearance=5.0,
    )

    assert candidates == []


def test_window_allows_back_door_with_minimum_gap() -> None:
    room: NormalizedRoom = {
        "name": "kitchen1",
        "type": "kitchen",
        "x": 0.0,
        "y": 0.0,
        "x_end": 40.0,
        "y_end": 20.0,
    }
    back_door: OpeningPayload = {
        "room_name": "kitchen1",
        "room_type": "kitchen",
        "opening_type": "backDoor",
        "side": "south",
        "x1": 0.0,
        "y1": 0.0,
        "x2": 8.0,
        "y2": 0.0,
    }

    candidates = build_window_candidates_for_room(
        room=room,
        exterior_sides={"south"},
        existing_openings=[back_door],
        window_width=8.0,
        door_clearance=5.0,
    )

    assert len(candidates) == 1


def test_veranda_layout_uses_living_veranda_main_door_connection() -> None:
    rooms = [
        {
            "name": "veranda1",
            "type": "veranda",
            "x": 0.0,
            "y": 0.0,
            "w": 20.0,
            "h": 10.0,
        },
        {
            "name": "livingRoom1",
            "type": "livingRoom",
            "x": 0.0,
            "y": 10.0,
            "w": 20.0,
            "h": 20.0,
        },
        {
            "name": "kitchen1",
            "type": "kitchen",
            "x": 20.0,
            "y": 10.0,
            "w": 20.0,
            "h": 20.0,
        },
    ]

    result = generate_openings(rooms)

    main_doors = [
        opening
        for opening in result["openings"]
        if opening.get("opening_type") == "mainDoor"
    ]
    assert len(main_doors) == 1

    main_door = main_doors[0]
    assert main_door["room_name"] == "livingRoom1"
    assert main_door.get("connected_room_name") == "veranda1"


def test_no_veranda_keeps_living_room_exterior_main_door() -> None:
    rooms = [
        {
            "name": "livingRoom1",
            "type": "livingRoom",
            "x": 0.0,
            "y": 0.0,
            "w": 30.0,
            "h": 20.0,
        },
        {
            "name": "kitchen1",
            "type": "kitchen",
            "x": 30.0,
            "y": 0.0,
            "w": 20.0,
            "h": 20.0,
        },
    ]

    result = generate_openings(rooms)

    main_doors = [
        opening
        for opening in result["openings"]
        if opening.get("opening_type") == "mainDoor"
    ]
    assert len(main_doors) == 1

    main_door = main_doors[0]
    assert main_door["room_name"] == "livingRoom1"
    assert not main_door.get("connected_room_name")
