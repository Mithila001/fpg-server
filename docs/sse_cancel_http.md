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