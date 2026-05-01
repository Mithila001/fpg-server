"""
Test suite for fpg_opening_v2 door constraint fixes:
- Bedroom door limits (1 without attached bath, 2 with attached bath)
- Bathroom-hallway door preference
"""

from app.algorithms.fpg_opening_v2.constratins.internal_doors_placement import (
    InternalDoorCandidate,
    Segment,
    select_internal_doors,
)
from app.algorithms.types.domain import ProcessedRoomData


def create_mock_room(
    name: str,
    room_type: str,
    x: float = 0,
    y: float = 0,
    width: float = 10,
    height: float = 10,
    original_index: int = 0,
) -> ProcessedRoomData:
    """Helper to create a mock ProcessedRoomData room for testing."""
    vertices = [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
    ]
    return ProcessedRoomData(
        name=name,
        type=room_type,
        original_index=original_index,
        vertices=vertices,
        area=width * height,
    )


def test_bedroom_without_attached_bathroom_max_one_door():
    """
    Test: Bedroom without attached bathroom should have max 1 door.
    Setup: Bedroom adjacent to hallway + livingroom (2 candidates).
    Expected: Only 1 door should be selected.
    """
    # Rooms: bedroom (0,0,10,10), hallway (10,0,20,10), livingroom (0,10,10,20)
    bedroom = create_mock_room(
        "bedroom1", "bedroom", x=0, y=0, width=10, height=10, original_index=0
    )
    hallway = create_mock_room(
        "hallway1", "hallway", x=10, y=0, width=10, height=10, original_index=1
    )
    livingroom = create_mock_room(
        "livingroom1", "livingroom", x=0, y=10, width=10, height=10, original_index=2
    )

    # Candidates: bedroom-hallway (vertical shared wall at x=10)
    #            bedroom-livingroom (horizontal shared wall at y=10)
    candidates = [
        InternalDoorCandidate(
            room_a=bedroom,
            room_b=hallway,
            segment=Segment(x1=10, y1=2, x2=10, y2=8),  # vertical wall, shared edge
            side_a="east",
            side_b="west",
        ),
        InternalDoorCandidate(
            room_a=bedroom,
            room_b=livingroom,
            segment=Segment(x1=2, y1=10, x2=8, y2=10),  # horizontal wall, shared edge
            side_a="north",
            side_b="south",
        ),
    ]

    doors = select_internal_doors(candidates, preferred_door_length=8.0)

    # Should select only 1 door for the bedroom
    bedroom_doors = [d for d in doors if d.room_name == "bedroom1"]
    assert len(bedroom_doors) == 1, (
        f"Expected 1 door for bedroom, got {len(bedroom_doors)}"
    )


def test_bedroom_with_attached_bathroom_allows_two_doors():
    """
    Test: Bedroom with attached bathroom should allow 2 doors.
    Setup: Bedroom adjacent to hallway + attachedBathroom (2 candidates).
    Expected: Both doors should be selected.
    """
    bedroom = create_mock_room(
        "bedroom1", "bedroom", x=0, y=0, width=10, height=10, original_index=0
    )
    hallway = create_mock_room(
        "hallway1", "hallway", x=10, y=0, width=10, height=10, original_index=1
    )
    attached_bath = create_mock_room(
        "attached_bath1",
        "attachedBathroom",
        x=0,
        y=10,
        width=10,
        height=10,
        original_index=2,
    )

    # Candidates: bedroom-hallway + bedroom-attachedBathroom
    candidates = [
        InternalDoorCandidate(
            room_a=bedroom,
            room_b=hallway,
            segment=Segment(x1=10, y1=2, x2=10, y2=8),
            side_a="east",
            side_b="west",
        ),
        InternalDoorCandidate(
            room_a=bedroom,
            room_b=attached_bath,
            segment=Segment(x1=2, y1=10, x2=8, y2=10),
            side_a="north",
            side_b="south",
        ),
    ]

    doors = select_internal_doors(candidates, preferred_door_length=8.0)

    # Should select both doors (social + bathroom)
    bedroom_doors = [d for d in doors if d.room_name == "bedroom1"]
    assert len(bedroom_doors) == 2, (
        f"Expected 2 doors for bedroom with attached bath, got {len(bedroom_doors)}"
    )


def test_bathroom_hallway_doors_prioritized():
    """
    Test: Bathroom doors connecting to hallway should be prioritized.
    Setup: Bathroom adjacent to hallway + livingroom (2 candidates).
           Hallway has max 1 door, so one must be skipped.
    Expected: Bathroom-hallway door selected; bathroom-livingroom skipped.
    """
    bathroom = create_mock_room(
        "bathroom1", "bathroom", x=0, y=0, width=10, height=10, original_index=0
    )
    hallway = create_mock_room(
        "hallway1", "hallway", x=10, y=0, width=10, height=10, original_index=1
    )
    livingroom = create_mock_room(
        "livingroom1", "livingroom", x=0, y=10, width=10, height=10, original_index=2
    )

    # Candidates: bathroom-livingroom (listed first, but should be lower priority)
    #            bathroom-hallway (listed second, but should be higher priority)
    candidates = [
        InternalDoorCandidate(
            room_a=bathroom,
            room_b=livingroom,
            segment=Segment(x1=2, y1=10, x2=8, y2=10),
            side_a="north",
            side_b="south",
        ),
        InternalDoorCandidate(
            room_a=bathroom,
            room_b=hallway,
            segment=Segment(x1=10, y1=2, x2=10, y2=8),
            side_a="east",
            side_b="west",
        ),
    ]

    doors = select_internal_doors(candidates, preferred_door_length=8.0)

    # Should select bathroom-hallway door (higher priority)
    # Should NOT select bathroom-livingroom door (would exceed bathroom max of 1)
    assert len(doors) == 1, f"Expected 1 door total, got {len(doors)}"
    assert doors[0].connected_room_name == "hallway1", (
        f"Expected bathroom door connected to hallway, got {doors[0].connected_room_name}"
    )


def test_multiple_bedrooms_independent_limits():
    """
    Test: Multiple bedrooms have independent door limits.
    Setup: bedroom1 without attached bath + bedroom2 with attached bath.
    Expected: bedroom1 max 1 door, bedroom2 max 2 doors.
    """
    bedroom1 = create_mock_room(
        "bedroom1", "bedroom", x=0, y=0, width=10, height=10, original_index=0
    )
    bedroom2 = create_mock_room(
        "bedroom2", "bedroom", x=20, y=0, width=10, height=10, original_index=1
    )
    hallway = create_mock_room(
        "hallway1", "hallway", x=10, y=0, width=10, height=10, original_index=2
    )
    attached_bath = create_mock_room(
        "attached_bath1",
        "attachedBathroom",
        x=20,
        y=10,
        width=10,
        height=10,
        original_index=3,
    )

    candidates = [
        # bedroom1 adjacent to hallway only
        InternalDoorCandidate(
            room_a=bedroom1,
            room_b=hallway,
            segment=Segment(x1=10, y1=2, x2=10, y2=8),
            side_a="east",
            side_b="west",
        ),
        # bedroom2 adjacent to hallway + attached bath
        InternalDoorCandidate(
            room_a=bedroom2,
            room_b=hallway,
            segment=Segment(x1=20, y1=2, x2=20, y2=8),
            side_a="west",
            side_b="east",
        ),
        InternalDoorCandidate(
            room_a=bedroom2,
            room_b=attached_bath,
            segment=Segment(x1=22, y1=10, x2=28, y2=10),
            side_a="north",
            side_b="south",
        ),
    ]

    doors = select_internal_doors(candidates, preferred_door_length=8.0)

    bedroom1_doors = [d for d in doors if d.room_name == "bedroom1"]
    bedroom2_doors = [d for d in doors if d.room_name == "bedroom2"]

    assert len(bedroom1_doors) == 1, (
        f"Expected 1 door for bedroom1, got {len(bedroom1_doors)}"
    )
    assert len(bedroom2_doors) == 2, (
        f"Expected 2 doors for bedroom2, got {len(bedroom2_doors)}"
    )


if __name__ == "__main__":
    print("Running test_bedroom_without_attached_bathroom_max_one_door...")
    test_bedroom_without_attached_bathroom_max_one_door()
    print("✓ PASS\n")

    print("Running test_bedroom_with_attached_bathroom_allows_two_doors...")
    test_bedroom_with_attached_bathroom_allows_two_doors()
    print("✓ PASS\n")

    print("Running test_bathroom_hallway_doors_prioritized...")
    test_bathroom_hallway_doors_prioritized()
    print("✓ PASS\n")

    print("Running test_multiple_bedrooms_independent_limits...")
    test_multiple_bedrooms_independent_limits()
    print("✓ PASS\n")

    print("All tests passed! ✓")
