You need to refactor/fix and modify `app\algorithms\fgp_score\score_functional\path_simulations` sections with following additional information

You should expect the data received in this structure (example)
print(f"Scoring Plan : {scoring_plan}\n ")
print(f"Tolerance : {tolerance}\n ")

Terminal output:
Scoring Plan : [ProcessedRoomData(type='bedroom', name='bedroom1', original_index=0, vertices=[(74.0, 79.0), (74.0, 124.0), (40.0, 124.0), (40.0, 79.0), (74.0, 79.0)], area=1530.0), ProcessedRoomData(type='bedroom', name='bedroom2', original_index=1, vertices=[(104.0, 99.0), (104.0, 129.0), (74.0, 129.0), (74.0, 99.0), (104.0, 99.0)], area=900.0), ProcessedRoomData(type='bathroom', name='bathroom1', original_index=2, vertices=[(104.0, 50.0), (104.0, 75.0), (88.0, 75.0), (88.0, 50.0), (104.0, 50.0)], area=400.0), ProcessedRoomData(type='kitchen', name='kitchen1', original_index=3, vertices=[(40.0, 79.0), (40.0, 129.0), (0.0, 129.0), (0.0, 79.0), (40.0, 79.0)], area=2000.0), ProcessedRoomData(type='attachedBathroom', name='attachedBathroom1', original_index=4, vertices=[(104.0, 75.0), (104.0, 99.0), (88.0, 99.0), (88.0, 75.0), (104.0, 75.0)], area=384.0), ProcessedRoomData(type='veranda', name='veranda1', original_index=5, vertices=[(30.0, 0.0), (30.0, 31.0), (0.0, 31.0), (0.0, 0.0), (30.0, 0.0)], area=930.0), ProcessedRoomData(type='garage', name='garage1', original_index=6, vertices=[(104.0, 0.0), (104.0, 50.0), (74.0, 50.0), (74.0, 0.0), (104.0, 0.0)], area=1500.0), ProcessedRoomData(type='diningRoom', name='diningRoom1', original_index=7, vertices=[(30.0, 31.0), (30.0, 79.0), (0.0, 79.0), (0.0, 31.0), (30.0, 31.0)], area=1440.0), ProcessedRoomData(type='livingRoom', name='livingRoom1', original_index=8, vertices=[(74.0, 9.0), (74.0, 79.0), (30.0, 79.0), (30.0, 9.0), (74.0, 9.0)], area=3080.0), ProcessedRoomData(type='hallway', name='hallway1', original_index=9, vertices=[(88.0, 50.0), (88.0, 99.0), (74.0, 99.0), (74.0, 50.0), (88.0, 50.0)], area=686.0)]

Tolerance : 1e-06

With `scoring_plan` you can construct the floor plan layout for the path simulations.

`app\algorithms\fgp_score\score_functional\path_simulations\path_sim_config.py` Should contain all configuration specifically related to This Path Simulation process to maintain centralize clear structure.
