### GOAL
Transform a set of individual room polygons into a "welded" wireframe layout. The output must consist of unique, non-overlapping wall segments where:
1. Shared walls between rooms are deduplicated into a single segment.
2. Perpendicular walls hitting the middle of another wall (T-junctions) create a clean "joint" (vertex injection).
3. All walls remain perfectly horizontal or vertical (alignment preservation).

---

### CORE ALGORITHM

#### 1. Grid Snapping (Normalization)
- Round all polygon vertex coordinates to a fixed precision (e.g., 0.1). 
- This ensures that nearly-parallel or nearly-touching walls become numerically identical.



#### 2. Axis-Aligned Decomposition
- Split all room polygons into individual segments.
- Group segments into two dictionaries:
    - **Horizontal:** `Key = Y-coordinate`, `Value = List of [X_start, X_end] intervals`.
    - **Vertical:** `Key = X-coordinate`, `Value = List of [Y_start, Y_end] intervals`.

#### 3. Vertex Injection (Joint Creation)
- For every Horizontal axis (Y):
    - Find all Vertical walls that have an endpoint on this Y-coordinate. 
    - Add the X-coordinate of those vertical endpoints to the Horizontal line's list of vertices.
- Repeat for Vertical axes (injecting Y-coordinates from Horizontal wall endpoints).



#### 4. Fragmentation & Occupancy Check
For each unique axis (e.g., a specific Y-coordinate):
1. **Sort & Unique:** Take all endpoints and injected vertices on that line, sort them, and remove duplicates $\{p_1, p_2, \dots, p_n\}$.
2. **Micro-Segments:** Create candidate segments $(p_i, p_{i+1})$.
3. **Validate:** Keep a candidate segment ONLY if it is covered by at least one original room interval.
    - `Logic: any(original_start <= candidate_start AND original_end >= candidate_end)`
4. **Result:** This automatically removes gaps and merges overlapping segments into a single continuous chain of joints.



---

### EXPECTED OUTPUT
- A list of unique wall segments: `[((x1, y1), (x2, y2)), ...]`
- A list of room metadata (Name, Type) with calculated center points for UI labeling.