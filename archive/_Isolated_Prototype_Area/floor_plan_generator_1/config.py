"""
Configuration file for floor plan generation.
Contains land dimensions and room specifications.
"""

# Floor Dimensions
FLOOR_WIDTH = 100
FLOOR_HEIGHT = 100
AddValue = 0

# Room specifications
ROOMS_DATA = [
    {"name": "Living Room", "min_w": 30 + AddValue, "min_h": 30 + AddValue},
    {"name": "Bedroom",     "min_w": 25 + AddValue, "min_h": 25 + AddValue},
    {"name": "Bedroom",     "min_w": 25 + AddValue, "min_h": 25 + AddValue},
    {"name": "Bedroom",     "min_w": 25 + AddValue, "min_h": 25 + AddValue},
    {"name": "Bedroom",     "min_w": 25 + AddValue, "min_h": 25 + AddValue},
    {"name": "Kitchen",     "min_w": 20 + AddValue, "min_h": 20 + AddValue},
    {"name": "Bathroom",    "min_w": 10 + AddValue, "min_h": 15 + AddValue}
]
