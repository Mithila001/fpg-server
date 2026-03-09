"""
Configuration defaults for floor plan generation.
Values here are used as fallbacks when no custom config is provided via the API.
"""

# Floor Dimensions (default)
FLOOR_WIDTH = 100
FLOOR_HEIGHT = 100

# Maximum allowed aspect ratio for rooms
MAX_ASPECT_RATIO_HEIGHT = 10
MAX_ASPECT_RATIO_WIDTH = 16

# Minimum floor area coverage (50%)
MIN_COVERAGE = 0.5

# Room size increments (set to 0 for no scaling)
ADD_VALUE = 0

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
DEFAULT_ROOMS_DATA = [
    {
        "name": "Living Room",
        "type": "LivingRoom",
        "min_w": livingRoomMinWidth + ADD_VALUE,
        "min_h": livingRoomMinHeight + ADD_VALUE,
        "max_w": livingRoomMaxWidth + ADD_VALUE,
        "max_h": livingRoomMaxHeight + ADD_VALUE,
    },
    {
        "name": "Bedroom",
        "type": "Bedroom",
        "min_w": bedroomMinWidth + ADD_VALUE,
        "min_h": bedroomMinHeight + ADD_VALUE,
        "max_w": bedroomMaxWidth + ADD_VALUE,
        "max_h": bedroomMaxHeight + ADD_VALUE,
    },
    {
        "name": "Bedroom 2",
        "type": "Bedroom",
        "min_w": bedroomMinWidth + ADD_VALUE,
        "min_h": bedroomMinHeight + ADD_VALUE,
        "max_w": bedroomMaxWidth + ADD_VALUE,
        "max_h": bedroomMaxHeight + ADD_VALUE,
    },
    {
        "name": "Bedroom 3",
        "type": "Bedroom",
        "min_w": bedroomMinWidth + ADD_VALUE,
        "min_h": bedroomMinHeight + ADD_VALUE,
        "max_w": bedroomMaxWidth + ADD_VALUE,
        "max_h": bedroomMaxHeight + ADD_VALUE,
    },
    {
        "name": "Kitchen",
        "type": "Kitchen",
        "min_w": kitchenMinWidth + ADD_VALUE,
        "min_h": kitchenMinHeight + ADD_VALUE,
        "max_w": kitchenMaxWidth + ADD_VALUE,
        "max_h": kitchenMaxHeight + ADD_VALUE,
    },
    {
        "name": "Bathroom",
        "type": "Bathroom",
        "min_w": bathroomMinWidth + ADD_VALUE,
        "min_h": bathroomMinHeight + ADD_VALUE,
        "max_w": bathroomMaxWidth + ADD_VALUE,
        "max_h": bathroomMaxHeight + ADD_VALUE,
    },
]
