"""
Configuration file for floor plan generation.
Contains land dimensions and room specifications.
"""

# Floor Dimensions
FLOOR_WIDTH = 100
FLOOR_HEIGHT = 100

# Note to be added to plot titles
PLOT_NOTE = "Complex Room Size Constraints Test"

# Maximum allowed aspect ratio for rooms (width/height or height/width)
MAX_ASPECT_RATIO_HEIGHT = 10
MAX_ASPECT_RATIO_WIDTH = 16

# Minimum floor area coverage
MIN_COVERAGE = 0.8

# This allows you to easily scale all rooms if you want to test
# larger minimum requirements later.
ADD_VALUE = 0

# Living Room
livingRoomMinWidth = 0
livingRoomMaxWidth = 100
livingRoomMinHeight = 0
livingRoomMaxHeight = 100
# Bedroom
bedroomMinWidth = 0
bedroomMaxWidth = 100
bedroomMinHeight = 0
bedroomMaxHeight = 100
# Kitchen
kitchenMinWidth = 0
kitchenMaxWidth = 100
kitchenMinHeight = 0
kitchenMaxHeight = 100
# Bathroom
bathroomMinWidth = 0
bathroomMaxWidth = 100
bathroomMinHeight = 0
bathroomMaxHeight = 100

# Room specifications
# These are the "Blueprints" that the Generator will use
# to create Room Objects.
ROOMS_DATA = [
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
