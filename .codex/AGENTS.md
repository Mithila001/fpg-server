# IMPORTANT: MUST FOllow Rules
- If you can read this file, Say "I can Read Agent.md File!" and simply move on with your work.
- DO NOT READ any files withing `/docs` folder, Those files are outdated.
- Avoid Implementing Test at `/test` unless specifically told by user.



# Project Context

This repository contains the backend server for an automated residential floor-plan generation system.

The system is designed to convert a user’s land details, floor dimensions, room requirements, and architectural constraints into a feasible single-story residential floor plan.

The backend contains the main computational logic of the project. It is responsible for:

- validating and normalizing incoming requirements,
- calculating the buildable area from the land boundary and setback rules,
- loading room-size, adjacency, and configuration constraints,
- managing long-running generation jobs,
- sending real-time progress updates through Server-Sent Events,
- exploring possible room-location hints,
- generating room layouts using constraint programming,
- refining and post-processing generated geometry,
- placing doors and windows,
- validating and scoring the final floor plan,
- and returning the completed structured result to the client.

The current generation pipeline broadly follows this flow:

1. Validate and normalize the request.
2. Determine the usable floor or buildable-space limits.
3. Prepare room requirements and active constraints.
4. Use Optuna-based exploration to identify promising spatial hint coordinates.
5. Pass those hints into a Google OR-Tools CP-SAT solver.
6. Generate an initial feasible room arrangement.
7. Run bounded refinement stages to improve the arrangement.
8. Apply geometric post-processing, such as wall extension, hallway union, coordinate snapping, veranda adjustment, and wall normalization.
9. Generate doors and windows.
10. Validate and score the completed layout.
11. Return the final result through the asynchronous job system.

The backend is primarily built with:

- Python
- FastAPI
- Uvicorn
- Pydantic
- PostgreSQL
- Google OR-Tools CP-SAT
- Optuna
- Shapely
- NetworkX
- NumPy, SciPy, and Pandas
- multiprocessing or background worker processes
- Server-Sent Events

The architecture separates API handling, job management, optimization, deterministic solving, geometric refinement, opening generation, scoring, persistence, and configuration into different concerns.

The project has evolved through several prototypes and algorithmic approaches. Earlier implementations may still exist in the repository, so file names, comments, and documents should not automatically be assumed to represent the current authoritative flow. Important behavior should be confirmed from the active routes, imports, runtime execution, configuration, tests, and current module relationships.

The project currently focuses on:

- single-story residential layouts,
- 2D room generation,
- convex land parcels,
- regulatory and dimensional plausibility,
- room adjacency and circulation,
- doors and windows,
- asynchronous generation,
- and visual floor-plan output.

It does not currently aim to produce complete construction drawings, structural engineering designs, electrical or plumbing layouts, or multi-story building plans.

The main architectural intent is to combine stochastic exploration with deterministic constraint solving. Optuna helps search for promising spatial arrangements, while CP-SAT enforces hard geometric and relational constraints. Post-processing then improves the raw solver output into a clearer and more architecturally usable floor plan.

Treat this file as high-level project context. Always verify exact class names, module names, active routes, data contracts, and implementation details from the current codebase.