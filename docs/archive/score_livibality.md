# Project Brief: Architectural Flow & Livability Scoring Engine

## 1. Problem Statement
Current floor plan validation only checks for "Usability" (e.g., no overlapping walls, valid aspect ratios). However, a "Usable" plan is not necessarily a "Good" plan. We need a way to score the **Livability** of a layout by analyzing how a human would actually experience and move through the space.

## 2. Core Concept: Human Circulation Simulation
Instead of static geometric analysis, we will simulate "Heuristic Walking Paths" between key functional points. By modeling realistic, non-robotic movement, we can identify traffic congestion, privacy leaks, and wasted space.

### Key Simulation Requirements:
* **Non-Robotic Pathfinding:** Paths must not be restricted to 90-degree turns. They should mimic human "drifting" and natural curves.
* **Traffic Overlap:** Identifying where "Public" paths (Entry to Living) intersect "Private" paths (Bedroom to Bathroom).
* **Dead Space Identification:** Detecting areas in hallways or rooms that are never touched by any heuristic path.
* **Furniture Interference:** Locating "Quiet Zones" in rooms that are free from cross-traffic, suitable for sofas or beds.

## 3. Technical Implementation Strategy

### A. The Walkable Mesh
* **Tool:** `Shapely`(Already Installed to python virtual environment), Or use better optuna if you have to
* **Logic:** Subtract all "Wall" polygons from the "Total Floor" polygon to create a "Navigation Mesh" (the walkable area). Also Subtract the Door Opening from those walls.

### B. Pathfinding & Smoothing
* **Tool:** `NetworkX` + `Scipy.interpolate` (Already Installed to python virtual environment)
* **Algorithm:** 1. Generate a fine-grained grid or graph over the walkable area.
    2. Use **A* (A-Star)** to find the shortest path between Point A and B.
    3. Apply **Chaikin’s Smoothing** or **Bézier Curves** to the path coordinates to create "Curvy/Natural" human movement.

### C. Traffic Heatmap
* **Logic:** Discretize the floor into a 2D array (Grid). For every simulation, increment the value of the cells touched by the path.
* **Result:** A weight-map where high values = high traffic; zero values = unused space.

## 4. Heuristic Simulation Points
For initial implementation, these are will be the path we simulate
1. Front Door to Kitchen Entrance
2. Front Door to Every Bedroom Entrance 
3. Front Door to Every Bathroom Entrance
4. All Bedroom Entrance to Closest Bathroom Entrance (Can pick only closest bathroom)
5. All Bedroom Entrance to Kitchen Entrance 

You will have to keep track of all room doors for this. 

## 5. Scoring Metrics (The Evaluator)

| Metric | Logic | Good/Bad |
| :--- | :--- | :--- |
| **Circulation Efficiency** | Ratio of Path Area vs. Total Room Area | Low ratio in Living Rooms is GOOD (less walking through the middle). |
| **Privacy Breach** | Path from Entry to Guest Bath crosses a Bedroom door view. | DEDUCTION (Privacy violation). |
| **Hallway Utility** | % of Hallway area utilized by at least one path. | High utility is GOOD; Low utility = Wasted space. |
| **Furniture Flexibility** | Largest contiguous area in Living/Bedroom with 0 traffic. | Large "Quiet Zones" = High score. |

## 6. Proposed Python Stack (Free/Open Source)
* **Shapely:** Geometric operations and intersection checks.
* **NetworkX:** Graph-based pathfinding (A*).
* **Numpy/Scipy:** Path smoothing and heatmap array math.
* **Matplotlib:** (Optional) Visualizing the heatmap during debugging.


## Other Details
- This specific scoring logic will place at `app/algorithms/fpg_rooms/fpg_score/score_functional/path_simulation`. All the files (Including Uitl files and Type files) should be placed withing `app/algorithms/fpg_rooms/fpg_score/score_functional/path_simulation` folder. This setup should not import existing util functions from outside of  `/score_functional/path_simulation` 

# Temp Dev Section
I created `app/algorithms/fpg_rooms/fpg_score/score_functional/path_simulation/dev` for you to implement a isolated temporary dev section. Here the main goal is to visualize the path simulation for debug. 

## How dev should work
- For each Scoring, Using matplotlib, create a image of showing all the simulated pathe (color coded based on Simulation Points)
- For the same image file, next to that path plot, create a another plot showing what hallways are unused (color them)
- Next to that, Create a another plotter showing the traffic intensity.

Overall, Single Saved png image, with 3 side by side plot (so it easier to look)
Image wil save at `test/outputs/path_score` folder with YYYY-MM-DD-HH-MM-SS-ms File Name 

Implement the scoring process at app/algorithms/fpg_rooms/fpg_score/score_functional/path_simulations
The score will be out of 10 of the total score_functional_section score value