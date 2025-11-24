"""
Configuration file for floor plan generation.
Contains land dimensions and room specifications.
"""

# Land Dimensions
LAND_WIDTH = 100
LAND_HEIGHT = 100

# Room specifications
ROOMS_DATA = [
    {"name": "Living Room", "min_w": 30, "min_h": 30},
    {"name": "Bedroom",     "min_w": 25, "min_h": 25},
    {"name": "Kitchen",     "min_w": 20, "min_h": 20},
    {"name": "Bathroom",    "min_w": 10, "min_h": 15}
]
