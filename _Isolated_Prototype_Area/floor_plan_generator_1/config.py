"""
Configuration file for floor plan generation.
Contains land dimensions and room specifications.
"""

# Land Dimensions
LAND_WIDTH = 100
LAND_HEIGHT = 100
ExtraIncrement = 0

# Room specifications
ROOMS_DATA = [
    {"name": "Living Room", "min_w": 30 + ExtraIncrement, "min_h": 30 + ExtraIncrement},
    {"name": "Bedroom",     "min_w": 25 + ExtraIncrement, "min_h": 25 + ExtraIncrement},
    {"name": "Bedroom",     "min_w": 25 + ExtraIncrement, "min_h": 25 + ExtraIncrement},
    {"name": "Kitchen",     "min_w": 20 + ExtraIncrement, "min_h": 20 + ExtraIncrement},
    {"name": "Bathroom",    "min_w": 10 + ExtraIncrement, "min_h": 15 + ExtraIncrement}
]
