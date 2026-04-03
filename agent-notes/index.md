# Agent Notes: Repository Index

## 1. Project Overview
- Repository: `fpg-server`
- Purpose: FastAPI backend for floor plan generation (FPG), including layout solver, optimization, and post-processing.
- Entry points:
  - `app/main.py` (FastAPI app startup, routing, request logging)
  - `app/routes/routes.py` (algorithm endpoints)

## 2. Key Components
- `app/algorithms`: suite of algorithm modules for building floor plans (`fpg_rooms`), opening generation (`fpg_opening`), buildable boundary handling (`fp_boundary_finder`), and land shrink geometry (`usable_land_space_finder`).
- `app/services`: orchestration layer, coordinating DB inputs, solver execution, post-processing, and API responses (`algorithm_manager`, `algorithm_manager_v2`, `buildable_space_manager`).
- `app/core`: config, database setup, and room-specific constants/rules.
- `app/crud`: CRUD database access for room templates and constraints.
- `app/schemas`: Pydantic/SQLModel schemas for DB models and API validation.
- `app/util`: helpers for unit conversion, requirement normalization, logging, and tracking.
- `docs` and `test`: design notes and unit tests.

## 3. Environment / Data
- `requirements.txt`: Python dependencies.
- `docker-compose.yml`: local service composition for API + PostgreSQL.
- `postgres_data/`: persisted DB volume in development.
- `seed.sql`: example DB seeding data.

## 4. Development Support
- `app/mock_data`: JSON mocks for local dev bypass.
- `test/dev`: debugging / plotting utilities (grid snapping, land boundary output).
- `logs`: JSONL outputs for API, scoring, optuna runs, and system logs.

## 5. Notes
- The project uses Optuna for solver parameter tuning (`fpg_optuna` module).
- Rate-limit is implemented in `app/routes/routes.py` for API endpoints.
- There are two pipeline versions: `algorithm_manager.py` (DB-first pipeline) and `algorithm_manager_v2.py` (client payload pipeline with stronger validation).
