# SSE + Cancel HTTP

This document explains a simple frontend-backend pattern for sending continuous progress updates from the server while still allowing the user to cancel the operation.

## How it works

1. **Start generation**
   - Frontend sends a `POST` request to begin floor plan generation.
   - Backend starts a job in the background and returns a `job_id` immediately.

2. **Receive progress updates**
   - Frontend opens an SSE connection to a dedicated endpoint, e.g. `/events?job_id=...`.
   - Backend sends events over that connection as trials complete, such as `trial=1/50`, `best_score=42`, or `status=searching`.
   - SSE is one-way: the server pushes updates, and the browser receives them automatically.

3. **Cancel if needed**
   - If the user cancels, the frontend sends a `POST /cancel` request with the `job_id`.
   - Backend marks the job canceled and stops work at the next safe checkpoint.
   - Backend can also send a final SSE event like `status=canceled`.

4. **Return the final result**
   - When the solver finds a good floor plan or completes the search, backend sends a final event over SSE.
   - Optionally, the frontend can also request the final payload from a separate endpoint once the job is complete.

## Why use SSE + Cancel HTTP

- **Simple frontend code**: browsers support `EventSource` natively for SSE.
- **Easy server-side implementation**: progress updates are sent on one connection, and cancel requests are separate HTTP calls.
- **Clear separation**: progress streaming is handled independently of command/control logic.
- **Good for this project**: trial-by-trial floor plan generation produces natural progress events, and cancel is a simple user action.

## Summary

Use SSE for the continuous progress feed and a normal HTTP cancel endpoint for stopping work. This gives a lightweight, robust architecture for generation progress + cancellation without the complexity of full WebSockets.

## Minimal job lifecycle (project choices)

- **Job ownership:** one job per user; server generates a temporary `job_id` (UUID4).
- **Execution model:** each job runs in its own OS process (worker wrapper) which calls the existing `run_fpg_pipeline_api()`; the parent process keeps a short-lived in-memory registry of jobs (status, pid, recent events, result).
- **Cancellation (hard stop):** cancel API calls `process.terminate()` for the job process and sets job result to `{"message":"Process Terminated"}` and status `TERMINATED`.
- **Progress events (SSE):** for now emit only the Optuna trial number as JSON (e.g. `{ "trial": 3 }`). The registry stores recent events so clients can reconnect and receive backlog.
- **Final output storage:** final result is kept in memory in the job registry (temporary) and available via result endpoint; not persisted to DB/files by default.
- **Reconnect behavior:** clients may reconnect to the SSE endpoint for the same `job_id` and receive cached events + remaining stream.
- **Timeout:** when a job exceeds configured timeout the parent terminates the process, sets status `TIMED_OUT` and result `{ "message": "Time Out" }`.
- **Concurrency rule:** one active job per user; server allows multiple users concurrently but enforces per-user single job.
- **Separation of concerns:** the worker wrapper invokes the generation flow as-is; SSE, job registry and cancel logic live outside and do not tightly couple into `run_fpg_pipeline_api()`.

Note: This in-memory registry is simplest for development. If you run multiple FastAPI workers, move the registry to a central store (Redis) or ensure job processes are spawned from a single coordinator process.
