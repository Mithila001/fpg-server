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
* **Tool:** `Shapely`
* **Logic:** Subtract all "Wall" polygons from the "Total Floor" polygon to create a "Navigation Mesh" (the walkable area).

### B. Pathfinding & Smoothing
* **Tool:** `NetworkX` + `Scipy.interpolate`
* **Algorithm:** 1. Generate a fine-grained grid or graph over the walkable area.
    2. Use **A* (A-Star)** to find the shortest path between Point A and B.
    3. Apply **Chaikin’s Smoothing** or **Bézier Curves** to the path coordinates to create "Curvy/Natural" human movement.

### C. Traffic Heatmap
* **Logic:** Discretize the floor into a 2D array (Grid). For every simulation, increment the value of the cells touched by the path.
* **Result:** A weight-map where high values = high traffic; zero values = unused space.

## 4. Heuristic Simulation Points
To evaluate a plan, the agent must simulate at least these 5 core paths:
1. **The Welcome:** Front Entrance $\rightarrow$ Kitchen (Groceries).
2. **The Guest:** Front Entrance $\rightarrow$ Common Bathroom.
3. **The Private:** Master Bedroom $\rightarrow$ Nearest Bathroom.
4. **The Social:** Kitchen $\rightarrow$ Living Room/Dining Area.
5. **The Maintenance:** Kitchen $\rightarrow$ Garage/Back Door.

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