You need to refactor/fix and modify `app\algorithms\fgp_score\score_functional\path_simulations` sections with following additional information

You should expect the data received in this structure (example)
print(f"Scoring Plan : {scoring_plan}\n ")
print(f"Tolerance : {tolerance}\n ")

Terminal output:
Scoring Plan : FloorPlanWithOpenings(floor_plan=[ProcessedRoomData(type='bedroom', name='bedroom1', original_index=0, vertices=[(74.0, 99.0), (74.0, 129.0), (31.0, 129.0), (31.0, 99.0), (74.0, 99.0)], area=1290.0), ProcessedRoomData(type='bedroom', name='bedroom2', original_index=1, vertices=[(104.0, 50.0), (104.0, 80.0), (74.0, 80.0), (74.0, 50.0), (104.0, 50.0)], area=900.0), ProcessedRoomData(type='bathroom', name='bathroom1', original_index=2, vertices=[(104.0, 104.0), (104.0, 129.0), (88.0, 129.0), (88.0, 104.0), (104.0, 104.0)], area=400.0), ProcessedRoomData(type='kitchen', name='kitchen1', original_index=3, vertices=[(31.0, 80.0), (31.0, 129.0), (0.0, 129.0), (0.0, 80.0), (31.0, 80.0)], area=1519.0), ProcessedRoomData(type='attachedBathroom', name='attachedBathroom1', original_index=4, vertices=[(104.0, 80.0), (104.0, 104.0), (88.0, 104.0), (88.0, 80.0), (104.0, 80.0)], area=384.0), ProcessedRoomData(type='veranda', name='veranda1', original_index=5, vertices=[(74.0, 0.0), (74.0, 31.0), (0.0, 31.0), (0.0, 0.0), (74.0, 0.0)], area=2294.0), ProcessedRoomData(type='garage', name='garage1', original_index=6, vertices=[(104.0, 0.0), (104.0, 50.0), (74.0, 50.0), (74.0, 0.0), (104.0, 0.0)], area=1500.0), ProcessedRoomData(type='diningRoom', name='diningRoom1', original_index=7, vertices=[(31.0, 31.0), (31.0, 80.0), (0.0, 80.0), (0.0, 31.0), (31.0, 31.0)], area=1519.0), ProcessedRoomData(type='livingRoom', name='livingRoom1', original_index=8, vertices=[(74.0, 31.0), (74.0, 99.0), (31.0, 99.0), (31.0, 31.0), (74.0, 31.0)], area=2924.0), ProcessedRoomData(type='hallway', name='hallway1', original_index=9, vertices=[(88.0, 80.0), (88.0, 129.0), (74.0, 129.0), (74.0, 80.0), (88.0, 80.0)], area=686.0)], openings=[OpeningData(room_name='bathroom1', room_type='bathroom', opening_type='internalDoor', side='west', x1=88.0, y1=112.5, x2=88.0, y2=120.5, connected_room_name='hallway1', connected_room_type='hallway'), OpeningData(room_name='bedroom1', room_type='bedroom', opening_type='internalDoor', side='south', x1=48.5, y1=99.0, x2=56.5, y2=99.0, connected_room_name='livingRoom1', connected_room_type='livingRoom'), OpeningData(room_name='bedroom2', room_type='bedroom', opening_type='internalDoor', side='north', x1=92.0, y1=80.0, x2=100.0, y2=80.0, connected_room_name='attachedBathroom1', connected_room_type='attachedBathroom'), OpeningData(room_name='bedroom2', room_type='bedroom', opening_type='internalDoor', side='west', x1=74.0, y1=61.0, x2=74.0, y2=69.0, connected_room_name='livingRoom1', connected_room_type='livingRoom'), OpeningData(room_name='kitchen1', room_type='kitchen', opening_type='internalDoor', side='east', x1=31.0, y1=85.5, x2=31.0, y2=93.5, connected_room_name='livingRoom1', connected_room_type='livingRoom'), OpeningData(room_name='veranda1', room_type='veranda', opening_type='mainDoor', side='north', x1=48.5, y1=31.0, x2=56.5, y2=31.0, connected_room_name='livingRoom1', connected_room_type='livingRoom'), OpeningData(room_name='garage1', room_type='garage', opening_type='internalDoor', side='west', x1=74.0, y1=36.5, x2=74.0, y2=44.5, connected_room_name='livingRoom1', connected_room_type='livingRoom'), OpeningData(room_name='diningRoom1', room_type='diningRoom', opening_type='internalDoor', side='east', x1=31.0, y1=51.5, x2=31.0, y2=59.5, connected_room_name='livingRoom1', connected_room_type='livingRoom'), OpeningData(room_name='livingRoom1', room_type='livingRoom', opening_type='internalDoor', side='east', x1=74.0, y1=85.5, x2=74.0, y2=93.5, connected_room_name='hallway1', connected_room_type='hallway'), OpeningData(room_name='kitchen1', room_type='kitchen', opening_type='backDoor', side='north', x1=11.5, y1=129.0, x2=19.5, y2=129.0, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE'), OpeningData(room_name='bedroom1', room_type='bedroom', opening_type='window', side='north', x1=44.5, y1=129.0, x2=60.5, y2=129.0, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE'), OpeningData(room_name='bedroom2', room_type='bedroom', opening_type='window', side='east', x1=104.0, y1=57.0, x2=104.0, y2=73.0, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE'), OpeningData(room_name='kitchen1', room_type='kitchen', opening_type='window', side='west', x1=0.0, y1=96.5, x2=0.0, y2=112.5, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE'), OpeningData(room_name='diningRoom1', room_type='diningRoom', opening_type='window', side='west', x1=0.0, y1=47.5, x2=0.0, y2=63.5, connected_room_name='OUTSIDE', connected_room_type='OUTSIDE')])

Tolerance : 1e-06

With `scoring_plan` you can construct the floor plan layout for the path simulations.

`app\algorithms\fgp_score\score_functional\path_simulations\path_sim_config.py` Should contain all configuration specifically related to This Path Simulation process to maintain centralize clear structure.

Now Rerun on the entire path simulation process to figure out everything will run accordingly without bugs and errors.

Update the `test\plotters\path_plotter.py` if required

When Come to scoring, Separate the internal scoring under these categories:

- Circulation Efficiency
- Privacy Score
- Hallway Utility
- Furniture Flexibility

Each one should score out of 100

And withing `app\algorithms\fgp_score\score_functional\path_simulations\run_path_simulation.py` Gather all and also get the `score_margin: float`
Now normalize the values to fit withing given score_margin cap and return the mark out of score_margin

When come to plotting, plot 4 scoring categories side by side 4 plots in the final plot. (Use classic theme plotting with clear visual)
Plotter will be called withing run_path_simulation.py

Do not call the path simulation function withing `app\algorithms\fgp_score\score_manager.py` let me do it.
