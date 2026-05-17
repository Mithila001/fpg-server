import sys
import os

from app.algorithms.types.domain import FpgRequirements
from app.algorithms.types.openings import FloorPlanWithOpenings, ProcessedRoomData, OpeningData
from app.algorithms.fgp_score.score_manager import score_manager

# Mock data from user
rooms = [
    ProcessedRoomData(type='bedroom', name='Bedroom 1', original_index=0, vertices=[(45.0, 102.0), (45.0, 139.0), (0.0, 139.0), (0.0, 102.0), (45.0, 102.0)], area=1665.0),
    ProcessedRoomData(type='bedroom', name='Bedroom 2', original_index=1, vertices=[(92.0, 75.0), (92.0, 109.0), (60.0, 109.0), (60.0, 75.0), (92.0, 75.0)], area=1088.0),
    ProcessedRoomData(type='kitchen', name='Kitchen 1', original_index=2, vertices=[(60.0, 0.0), (60.0, 30.0), (21.0, 30.0), (21.0, 0.0), (60.0, 0.0)], area=1170.0),
    ProcessedRoomData(type='bathroom', name='Bathroom 1', original_index=3, vertices=[(76.0, 50.0), (76.0, 75.0), (60.0, 75.0), (60.0, 50.0), (76.0, 50.0)], area=400.0),
    ProcessedRoomData(type='diningRoom', name='Dining Room 1', original_index=4, vertices=[(92.0, 109.0), (92.0, 139.0), (60.0, 139.0), (60.0, 109.0), (92.0, 109.0)], area=960.0),
    ProcessedRoomData(type='garage', name='Garage 1', original_index=5, vertices=[(92.0, 0.0), (92.0, 50.0), (60.0, 50.0), (60.0, 0.0), (92.0, 0.0)], area=1600.0),
    ProcessedRoomData(type='veranda', name='Veranda 1', original_index=6, vertices=[(21.0, 0.0), (21.0, 30.0), (0.0, 30.0), (0.0, 0.0), (21.0, 0.0)], area=630.0),
    ProcessedRoomData(type='attachedBathroom', name='Attached Bathroom 1', original_index=7, vertices=[(92.0, 50.0), (92.0, 75.0), (76.0, 75.0), (76.0, 50.0), (92.0, 50.0)], area=400.0),
    ProcessedRoomData(type='livingRoom', name='livingRoom1', original_index=8, vertices=[(45.0, 30.0), (45.0, 102.0), (0.0, 102.0), (0.0, 30.0), (45.0, 30.0)], area=3240.0),
    ProcessedRoomData(type='hallway', name='hallway1', original_index=9, vertices=[(60.0, 30.0), (60.0, 134.0), (45.0, 134.0), (45.0, 30.0), (60.0, 30.0)], area=1560.0)
]

openings = [
    OpeningData(room_name='Bedroom 2', room_type='bedroom', opening_type='internalDoor', side='south', x1=80.0, y1=75.0, x2=88.0, y2=75.0, connected_room_name='Attached Bathroom 1', connected_room_type='attachedBathroom'),
    OpeningData(room_name='Bathroom 1', room_type='bathroom', opening_type='internalDoor', side='west', x1=60.0, y1=58.5, x2=60.0, y2=66.5, connected_room_name='hallway1', connected_room_type='hallway'),
    OpeningData(room_name='Bedroom 1', room_type='bedroom', opening_type='internalDoor', side='east', x1=45.0, y1=114.0, x2=45.0, y2=122.0, connected_room_name='hallway1', connected_room_type='hallway'),
    OpeningData(room_name='Kitchen 1', room_type='kitchen', opening_type='internalDoor', side='north', x1=48.5, y1=30.0, x2=56.5, y2=30.0, connected_room_name='hallway1', connected_room_type='hallway'),
    OpeningData(room_name='Bedroom 2', room_type='bedroom', opening_type='internalDoor', side='west', x1=60.0, y1=88.0, x2=60.0, y2=96.0, connected_room_name='hallway1', connected_room_type='hallway'),
    OpeningData(room_name='Dining Room 1', room_type='diningRoom', opening_type='internalDoor', side='west', x1=60.0, y1=117.5, x2=60.0, y2=125.5, connected_room_name='hallway1', connected_room_type='hallway'),
    OpeningData(room_name='Garage 1', room_type='garage', opening_type='internalDoor', side='west', x1=60.0, y1=36.0, x2=60.0, y2=44.0, connected_room_name='hallway1', connected_room_type='hallway'),
    OpeningData(room_name='Veranda 1', room_type='veranda', opening_type='mainDoor', side='north', x1=6.5, y1=30.0, x2=14.5, y2=30.0, connected_room_name='livingRoom1', connected_room_type='livingRoom'),
    OpeningData(room_name='livingRoom1', room_type='livingRoom', opening_type='internalDoor', side='east', x1=45.0, y1=62.0, x2=45.0, y2=70.0, connected_room_name='hallway1', connected_room_type='hallway'),
    OpeningData(room_name='Kitchen 1', room_type='kitchen', opening_type='backDoor', side='south', x1=36.5, y1=0.0, x2=44.5, y2=0.0, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE'),
    OpeningData(room_name='Bedroom 1', room_type='bedroom', opening_type='window', side='north', x1=14.5, y1=139.0, x2=30.5, y2=139.0, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE'),
    OpeningData(room_name='Bedroom 2', room_type='bedroom', opening_type='window', side='east', x1=92.0, y1=84.0, x2=92.0, y2=100.0, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE'),
    OpeningData(room_name='Dining Room 1', room_type='diningRoom', opening_type='window', side='east', x1=92.0, y1=116.0, x2=92.0, y2=132.0, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE'),
    OpeningData(room_name='livingRoom1', room_type='livingRoom', opening_type='window', side='west', x1=0.0, y1=58.0, x2=0.0, y2=74.0, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE')
]

scoring_plan = FloorPlanWithOpenings(floor_plan=rooms, openings=openings)

class MockConfig:
    score_geometry_tolerance = 1e-6
    floor_plan_width = 100.0
    floor_plan_height = 100.0
    inward_pocket_max_length = 20.0

class MockReqs:
    config = MockConfig()
    relation_constraints = []

reqs = MockReqs()

print("Running score_manager...")
result = score_manager(scoring_plan, reqs)
print("Done!")
