# FPG Server — Constraint-Driven Residential Floor Plan Generation Engine

Backend and computational engine for generating **2D single-story residential floor plans** from land geometry and room requirements.

Instead of treating floor-plan generation as a free-form content generation task, the engine models it as a **spatial optimization and constraint-solving problem**. Room dimensions, adjacency, circulation, frontage, setbacks, and other spatial rules are encoded into the generation pipeline so that layouts are produced from explicit planning logic rather than visual approximation alone.

## What Problem It Solves

Early residential planning often starts with rough room ideas that may not fit the available land, respect setbacks, or form a practical layout. The server helps reduce this trial-and-error by converting site and room requirements into structured candidate plans that can be evaluated and refined before professional architectural development.

## Generation Flow

```text
Land Geometry + Room Requirements
              |
              v
Buildable-Space Estimation
              |
              v
Requirement Validation & Normalization
              |
              v
Candidate Spatial Search (Optuna)
              |
              v
Constraint-Based Layout Synthesis (OR-Tools CP-SAT)
              |
              v
Iterative Solver Refinement
              |
              v
Geometric Post-Processing
              |
              v
Door & Window Placement
              |
              v
Floor Plan Evaluation / Scoring
              |
              v
Generated 2D Floor Plan
```

## Core Capabilities

- Calculates a usable planning region from land boundaries and configured setback rules.
- Validates room requirements before expensive generation begins.
- Uses **Optuna** to explore promising spatial arrangements and produce location hints for the solver.
- Uses **Google OR-Tools CP-SAT** to generate room geometry under hard spatial constraints.
- Supports rules for room dimensions, non-overlap, adjacency, circulation, frontage behavior, and shared boundaries.
- Separates **hard constraints** from **soft optimization objectives**, allowing feasibility and layout quality to be handled independently.
- Applies iterative refinement to improve an existing feasible arrangement without completely rebuilding it.
- Uses geometric post-processing for alignment, hallway merging, grid normalization, wall cleanup, and rectilinear refinement.
- Generates doors and windows after the main room layout has been established.
- Evaluates completed layouts using geometric and functional scoring checks.
- Runs computational work asynchronously and exposes real-time progress through **Server-Sent Events (SSE)**.

## Architecture

The server is organized as a multi-stage pipeline so that expensive constraint solving is not responsible for every decision at once.

### 1. Buildable-Space Estimation
Interprets land geometry and setback configuration to identify the region available for the building footprint.

### 2. Requirement Preparation
Normalizes room counts, dimensions, aspect requirements, and active relationships into solver-ready input.

### 3. Spatial Candidate Search
Optuna explores candidate room-location hints on a reduced search space. These hints provide direction without fixing the final geometry.

### 4. CP-SAT Floor Plan Solver
Google OR-Tools CP-SAT creates the actual room layout and enforces non-negotiable geometric and relational conditions.

### 5. Refinement & Post-Processing
Solver refinement improves the feasible layout, while geometric post-processing repairs local irregularities and prepares the plan for openings.

### 6. Opening Generation & Scoring
Doors and windows are placed using spatial rules, followed by final checks for geometric validity and practical layout quality.

## API & Job Processing

Floor-plan generation can take significantly longer than a normal API request. The FastAPI application therefore uses an asynchronous job workflow:

1. Client submits a generation request.
2. Server creates a job and returns its identifier.
3. Generation runs separately from the request lifecycle.
4. Progress events are streamed to the client through SSE.
5. The completed floor plan is returned when processing finishes.

## Tech Stack

- **Python**
- **FastAPI** / Uvicorn
- **Pydantic**
- **Google OR-Tools CP-SAT**
- **Optuna**
- **Shapely**
- **NetworkX**
- **NumPy / SciPy / Pandas**
- **PostgreSQL**
- **REST APIs**
- **Server-Sent Events (SSE)**
- **Docker / Docker Compose**

## Running Locally

### Prerequisites

- Docker
- Docker Compose
- Recommended: 4-core CPU or better and at least 8 GB RAM

### Start the API and Database

```bash
docker-compose up --build
```

The Docker setup starts the API and PostgreSQL database and initializes the required application data.

## Project Scope

Current focus:

- Single-story residential layouts
- 2D floor-plan generation
- Convex land parcels
- Configurable room requirements
- Constraint-driven room placement
- Buildable-space estimation
- Automated doors and windows
- Layout refinement and scoring

The generated output is intended for **early-stage residential planning and layout exploration**. It is not a replacement for professional architectural, structural, or construction documentation, and the current rule set does not represent every municipality-specific planning or fenestration requirement.

## Related Repository

The companion frontend provides interactive land editing, room configuration, generation progress tracking, and 2D floor-plan visualization.
