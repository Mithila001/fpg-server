# Project Context

This project contains the backend server for an automated residential floor-plan generation system.

The system converts user land information, floor dimensions, room requirements, and architectural constraints into a feasible residential floor plan.

---

# Coordinate System

The entire project uses a single canonical Cartesian coordinate system.

All algorithms, geometry operations, visualizations, API contracts, tests, and generated floor plans **must** follow this convention.

```text
                Back (+Y)

                    ↑
                    |
                    |
 Left (-X) ---------+--------- Right (+X)
                    |
                    |
                    ↓

               Front (-Y)
```

Direction mapping:

| Direction | Coordinate Axis |
|-----------|-----------------|
| Front | **-Y** |
| Back | **+Y** |
| Left | **-X** |
| Right | **+X** |

This orientation is considered part of the project's architecture and must remain consistent throughout the entire codebase.

---

# House Orientation

The front of every generated floor plan faces the **negative Y (-Y)** direction.

Examples:

- Front veranda should normally be positioned toward **-Y**.
- The main entrance should normally face **-Y**.
- A garage (when present) should be placed on the front edge (**-Y**), either on the front-left or front-right side.
- Any "front", "back", "left", or "right" rule throughout the project refers to this coordinate system.

Algorithms must **never** assume that the front is +Y or that another orientation is used.

---

# Measurement System

The project uses **integer project units**.

```text
10 project units = 1 meter
```

Therefore:

| Project Units | Real Length |
|---------------|-------------|
| 1 | 10 cm |
| 5 | 50 cm |
| 10 | 1.0 m |
| 20 | 2.0 m |
| 80 | 8.0 m |
| 120 | 12.0 m |

The project does **not** use fractional units.

All geometry, room dimensions, coordinates, wall locations, door positions, window positions, and constraints should operate using integer project units unless a specific algorithm explicitly requires temporary floating-point calculations.

---

# Floor Plan Coordinates

Every generated floor plan exists within this coordinate system.

Example:

```text
Floor Width  = 120 units
Floor Length = 110 units
```

represents

```text
12 m × 11 m
```

All room coordinates, candidate search positions, solver geometry, post-processing, openings, scoring, and visualization use the same coordinate space.

---

# Project-Wide Convention

Every component of the project must follow this coordinate system, including but not limited to:

- Candidate Search
- Candidate Scoring
- Floor Plan Solver
- Floor Plan Post Processing
- Floor Plan Openings
- Floor Plan Scoring
- Visualization
- API Contracts
- Tests
- Mock Data

No module should redefine or reinterpret the coordinate orientation.

---

# AI Coding Agent Instructions

When implementing or modifying any geometry-related feature:

- Always treat **Front** as **-Y**.
- Always treat **Back** as **+Y**.
- Always treat **Left** as **-X**.
- Always treat **Right** as **+X**.
- Always use **10 project units = 1 meter**.
- Use integer project units throughout the project unless a specific algorithm requires temporary floating-point calculations.
- Do not introduce a different coordinate orientation.
- If a feature references "front", "back", "left", or "right", interpret those directions according to this document.
- If adding new geometry algorithms, constraints, visualization features, or API contracts, they must remain compatible with this coordinate system.
