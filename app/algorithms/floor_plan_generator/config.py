"""
Configuration defaults for floor plan generation.
Values here are used as fallbacks when no custom config is provided via the API.
"""

from .types.room import RoomData

# Floor Dimensions (default)
FLOOR_WIDTH = 200
FLOOR_HEIGHT = 200
# Maximum allowed aspect ratio for rooms
MAX_ASPECT_RATIO_HEIGHT = 10
MAX_ASPECT_RATIO_WIDTH = 16

# Minimum floor area coverage (50%)
MIN_COVERAGE = 0.5

# Room size increments (set to 0 for no scaling)
ADD_VALUE = 0

# Hallway dimensions
# Fixed narrow dimension — the solver enforces exactly this value for
# whichever of width/height is the "short" side.
HALLWAY_WIDTH = 5
# Minimum length of the long side (the solver may extend it further).
HALLWAY_MIN_LENGTH = 5

# Living Room
livingRoomMinWidth = 30
livingRoomMaxWidth = 50
livingRoomMinHeight = 30
livingRoomMaxHeight = 50
# Bedroom
bedroomMinWidth = 10
bedroomMaxWidth = 40
bedroomMinHeight = 10
bedroomMaxHeight = 40
# Kitchen
kitchenMinWidth = 20
kitchenMaxWidth = 40
kitchenMinHeight = 20
kitchenMaxHeight = 40
# Bathroom
bathroomMinWidth = 5
bathroomMaxWidth = 15
bathroomMinHeight = 5
bathroomMaxHeight = 15

# Default room specifications used when no rooms_data is provided
DEFAULT_ROOMS_DATA: list[RoomData] = [
    RoomData("Living Room", "livingRoom", livingRoomMinWidth + ADD_VALUE, livingRoomMinHeight + ADD_VALUE, livingRoomMaxWidth + ADD_VALUE, livingRoomMaxHeight + ADD_VALUE),
    RoomData("Bedroom", "bedroom", bedroomMinWidth + ADD_VALUE, bedroomMinHeight + ADD_VALUE, bedroomMaxWidth + ADD_VALUE, bedroomMaxHeight + ADD_VALUE),
    RoomData("Bedroom 2", "bedroom", bedroomMinWidth + ADD_VALUE, bedroomMinHeight + ADD_VALUE, bedroomMaxWidth + ADD_VALUE, bedroomMaxHeight + ADD_VALUE),
    RoomData("Bedroom 3", "bedroom", bedroomMinWidth + ADD_VALUE, bedroomMinHeight + ADD_VALUE, bedroomMaxWidth + ADD_VALUE, bedroomMaxHeight + ADD_VALUE),
    RoomData("Kitchen", "kitchen", kitchenMinWidth + ADD_VALUE, kitchenMinHeight + ADD_VALUE, kitchenMaxWidth + ADD_VALUE, kitchenMaxHeight + ADD_VALUE),
    RoomData("Bathroom", "bathroom", bathroomMinWidth + ADD_VALUE, bathroomMinHeight + ADD_VALUE, bathroomMaxWidth + ADD_VALUE, bathroomMaxHeight + ADD_VALUE),
]
