# Job Lifecycle & Execution Management Implementation Plan

## 1. Core Architecture & API Contract

- **Async Pattern:** Main endpoints (`/format/v2` and `/buildable-space`) follow an asynchronous pattern.
  - **Response:** Return `202 Accepted` immediately with a unique `job_id` (UUID4).
  - **Processing:** The server spawns a separate OS process for each job to ensure application responsiveness and allow for a "hard stop" termination.
- **Separation of Concerns:** Job management logic (registry, process handling) is decoupled from the internal floor plan generation logic (Optuna, Solver, Post-Processing).

## 2. Job Registry & Status Tracking

- **Registry:** A short-lived in-memory registry (or Redis) serves as the source of truth.
- **Stored Data:**
  - `PID`: OS process ID for termination.
  - `Status`: SEARCHING, TERMINATED, TIMED_OUT, COMPLETED.
  - `Metadata`: Recent event history and final results for client reconnection.
- **Job Cleanup:** Jobs remain in the registry for a configurable period (default: 1 minute) before being purged.

## 3. Concurrency & Safeguards

- **One-Job-Per-User Rule:**
  - A user can only run one job at a time across either `/format/v2` or `/buildable-space`.
  - If a new request is made while a process is active, the API returns a "Process is Already Running" message.
  - **Note:** Rate limiting features can be removed in favor of this state-based lockout.
- **Client Control:** If a user needs to start a new job while one is active, the client must explicitly call the `/cancel` endpoint first. Other wise, user will get "Already Job is running" message if kept asking for new job.

## 4. Termination & Timeouts

- **Global Timeout:**
  - `FPG_GENERATION_API_TIMEOUT = 60` (defined in `app/core/config.py`).
  - If a job exceeds this limit, the registry automatically terminates the OS process.
  - **Optuna Logic:** Job-level timeouts will automatically terminate Optuna trial sampling via the process-level hard stop.
- **Manual Cancellation:**
  - Endpoint: `POST /cancel`.
  - Action: Look up PID in the registry and invoke a system-level terminate signal.
  - **Priority:** Immediate cutoff of client-server processing. Minor log artifacts are acceptable to keep implementation simple.

## 5. Configuration (app/core/config.py)

The following variables should be managed in the core configuration:

- `FPG_GENERATION_API_TIMEOUT`: Maximum execution time for jobs (default 60s).
- `JOB_REGISTRY_CLEANUP_DELAY`: Time to keep job data after completion/cancellation (default 60s).

## 6. Deployment Strategy

- **Model:** Lightweight implementation using standard Python `multiprocessing` or `subprocess` for OS process management. Or any other suitable solution.
- **Simplicity:** Prioritize a robust, "not over-engineered" setup that can be managed within the existing environment without complex external dependencies. Prefer implementation where the internal Floor plan does not tightly coupled with job management process.
