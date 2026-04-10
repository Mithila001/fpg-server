# FPG Room Scoring

This package implements the new 4-section scoring flow for FPG room layouts.

## Score Sections
The score is divided into four equal sectors, each worth up to 25 points:

1. `score_critical`
   - Evaluates hard critical checks using pass/fail logic.
   - Checks include room geometry, overlap, adjacency, envelope/staircase bounds, empty space, and inward pocket.
   - The section score is `25 * (passed_checks / total_checks)`.
   - If this section does not score full 25 points, the entire scoring flow stops and the other sections return 0.

2. `score_room`
   - Reuses the existing coverage and rectangularity logic.
   - The raw scores are combined and normalized to a 25-point section.
   - This section only runs when `score_critical` is full 25.

3. `score_functional`
   - Placeholder functional scoring section.
   - Runs only when `score_critical + score_room >= 40`.
   - Currently returns a score based on executable placeholder checks.

4. `score_extra`
   - Placeholder extra scoring section.
   - Also runs only when `score_critical + score_room >= 40`.
   - Currently returns a score based on executable placeholder checks.

## Gate Rules
- Gate 1: If `score_critical < 25`, then `score_room`, `score_functional`, and `score_extra` are all set to 0.
- Gate 2: If `score_critical == 25` but `score_critical + score_room < 40`, then `score_functional` and `score_extra` are set to 0.

## Package Structure
- `score_manager.py` — orchestrates the full scoring flow and implements gating rules.
- `score_critical/` — critical pass/fail checks.
- `score_room/` — coverage and rectangularity room scoring.
- `score_functional/` — placeholder functional scoring.
- `score_extra/` — placeholder extra scoring.
- `types/` — shared scoring report types.

## Logging
The manager logs structured events for:
- critical scoring results,
- room scoring results,
- gate blocking in the second phase,
- final completion with total scores.
