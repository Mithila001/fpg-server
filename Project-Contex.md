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

# Room Type Convention

`app.algorithms.types_new.RoomType` is the single canonical room-type
definition for the entire Python project.

- Serialized API and JSON inputs represent room types with exact enum values,
  such as `"garage"` for `RoomType.GARAGE`.
- Every input boundary must parse those values strictly. Case changes, aliases,
  spaces, and hyphenated alternatives must be rejected as validation errors.
- After deserialization, server code, configuration, tests, and manual runners
  must store, pass, index, and compare room types using `RoomType` members only.
- Do not introduce hardcoded room-type strings or room-type normalization and
  alias tables in Python code.
- Access `.value` only when serializing, displaying, or logging a room type.
  JSON fixtures and API responses may contain the canonical string values.
- Room identifiers, display names, and non-room-type category labels remain
  strings and are not governed by this convention.

---

# Generated Output Convention

All newly generated visualization images, JSON artifacts, and application logs
must be stored under the root-level `output/` directory. Set `OUTPUT_ROOT` to
override this location; relative values are resolved from the running process.

```text
output/
├── visualizations/
│   ├── candidate_search/<timestamp>_<request-id>/
│   └── floor_plan_general/<timestamp>_<request-id>/
├── json/
│   └── <feature>/<timestamp>_<debug-or-run-name>/
└── logs/
    └── <timestamp>_server-<process-id>/
```

Timestamps use UTC and the sortable `YYYYMMDDTHHMMSSffffffZ` format. For
example, `20260722T061530123456Z` represents a UTC instant with microsecond
precision.

Runtime-created folders and files use these templates:

```text
Folder: <timestamp>_<descriptive-run-name>/
File:   <timestamp>_<descriptive-name>_<short-unique-id>.<extension>
```

The root and the stable category/feature folders (`visualizations`, `json`,
`logs`, and their feature names) are organizational exceptions and do not need
timestamps. Timestamp requirements apply to runtime-created run folders and
artifact files.

Algorithms must return data without writing visualization artifacts or knowing
about Matplotlib. Pipeline and explicit debug/manual orchestration code own
visualization and artifact persistence. Production generation results remain
API responses and are not automatically saved as JSON files.

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
- Send every new generated PNG, JSON artifact, and file log through the root `output/` convention above.
