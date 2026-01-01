"""
Configuration file for floor plan generation.
Contains land dimensions and room specifications.
"""

# Floor Dimensions
FLOOR_WIDTH = 100
FLOOR_HEIGHT = 100

# This allows you to easily scale all rooms if you want to test 
# larger minimum requirements later.
ADD_VALUE = 0

# Room specifications
# These are the "Blueprints" that the Generator will use 
# to create Room Objects.
ROOMS_DATA = [
    {"name": "Living Room", "min_w": 30 + ADD_VALUE, "min_h": 30 + ADD_VALUE},
    {"name": "Bedroom 1",   "min_w": 25 + ADD_VALUE, "min_h": 25 + ADD_VALUE},
    {"name": "Bedroom 2",   "min_w": 25 + ADD_VALUE, "min_h": 25 + ADD_VALUE},
    {"name": "Bedroom 3",   "min_w": 25 + ADD_VALUE, "min_h": 25 + ADD_VALUE},
    {"name": "Bedroom 4",   "min_w": 25 + ADD_VALUE, "min_h": 25 + ADD_VALUE},
    {"name": "Kitchen",     "min_w": 20 + ADD_VALUE, "min_h": 20 + ADD_VALUE},
    {"name": "Bathroom",    "min_w": 10 + ADD_VALUE, "min_h": 15 + ADD_VALUE}
]