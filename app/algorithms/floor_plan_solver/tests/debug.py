from __future__ import annotations

import argparse
import json
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from app.algorithms.floor_plan_solver import (
    FloorPlanSolveRequest,
    FloorPlanSolveResult,
    FloorPlanSolver,
    GenerationProfile,
    INITIAL_GENERATION_PROFILE,
    REFINEMENT_A_PROFILE,
    REFINEMENT_B_PROFILE,
)

from .builders import (
    UNIT_SIZE_CENTIMETERS,
    UNITS_PER_METER,
    build_realistic_candidate_hints,
    build_realistic_generation_spec,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: _jsonable(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _runtime_profile(
    profile: GenerationProfile,
    max_time_seconds: float | None,
) -> GenerationProfile:
    if max_time_seconds is None:
        return profile
    return replace(
        profile,
        solver=replace(
            profile.solver,
            max_time_seconds=max_time_seconds,
        ),
    )


def _write_stage_output(
    filename: str,
    request: FloorPlanSolveRequest,
    result: FloorPlanSolveResult,
) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    payload = {
        "measurement": {
            "units_per_meter": UNITS_PER_METER,
            "unit_size_centimeters": UNIT_SIZE_CENTIMETERS,
            "dimensions_use_whole_project_units": True,
        },
        "request": _jsonable(request),
        "result": _jsonable(result),
    }
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def _print_result(result: FloorPlanSolveResult, output_path: Path) -> None:
    room_count = len(result.floor_plan.rooms) if result.floor_plan else 0
    print(
        f"{result.profile_name}: status={result.status.value}, "
        f"rooms={room_count}, "
        f"wall_time={result.diagnostics.wall_time_seconds:.3f}s, "
        f"output={output_path}"
    )


def run_debug_pipeline(max_time_seconds: float | None = None) -> int:
    solver = FloorPlanSolver()
    specification = build_realistic_generation_spec()
    hints = build_realistic_candidate_hints()

    initial_profile = _runtime_profile(
        INITIAL_GENERATION_PROFILE,
        max_time_seconds,
    )
    initial_request = FloorPlanSolveRequest(
        specification=specification,
        profile=initial_profile,
        candidate_hints=hints,
    )
    initial_result = solver.solve(initial_request)
    initial_path = _write_stage_output(
        "initial_generation.json",
        initial_request,
        initial_result,
    )
    _print_result(initial_result, initial_path)
    if initial_result.floor_plan is None:
        return 1

    refinement_a_profile = _runtime_profile(
        REFINEMENT_A_PROFILE,
        max_time_seconds,
    )
    refinement_a_request = FloorPlanSolveRequest(
        specification=specification,
        profile=refinement_a_profile,
        existing_floor_plan=initial_result.floor_plan,
    )
    refinement_a_result = solver.solve(refinement_a_request)
    refinement_a_path = _write_stage_output(
        "refinement_a.json",
        refinement_a_request,
        refinement_a_result,
    )
    _print_result(refinement_a_result, refinement_a_path)
    if refinement_a_result.floor_plan is None:
        return 1

    refinement_b_profile = _runtime_profile(
        REFINEMENT_B_PROFILE,
        max_time_seconds,
    )
    refinement_b_request = FloorPlanSolveRequest(
        specification=specification,
        profile=refinement_b_profile,
        existing_floor_plan=refinement_a_result.floor_plan,
    )
    refinement_b_result = solver.solve(refinement_b_request)
    refinement_b_path = _write_stage_output(
        "refinement_b.json",
        refinement_b_request,
        refinement_b_result,
    )
    _print_result(refinement_b_result, refinement_b_path)
    return 0 if refinement_b_result.solved else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the real floor-plan solver through initial generation, "
            "Refinement A, and Refinement B, then save JSON outputs."
        )
    )
    parser.add_argument(
        "--max-time-seconds",
        type=float,
        default=None,
        help=(
            "Optional per-stage solver limit. Omit it to use the exact built-in "
            "profile limits."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.max_time_seconds is not None and args.max_time_seconds <= 0:
        raise SystemExit("--max-time-seconds must be greater than zero")
    return run_debug_pipeline(args.max_time_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
