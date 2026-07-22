from __future__ import annotations

from app.algorithms.floor_plan_scoring import score_floor_plan
from app.util.output_paths import create_artifact_path, create_run_directory

from .builders import build_realistic_case
from .serialization import write_json

def main() -> None:
    floor_plan, specification = build_realistic_case()
    result = score_floor_plan(floor_plan, specification)
    output_directory = create_run_directory(
        "json", "floor_plan_scoring", "floor-plan-scoring-debug"
    )
    output_path = write_json(
        create_artifact_path(
            output_directory, "floor-plan-scoring-result", "json"
        ),
        result,
    )

    print(f"Scoring completed: {result.total_score:.4f}/100")
    print(f"Critical gate passed: {result.passed_critical}")
    print(f"JSON output: {output_path}")


if __name__ == "__main__":
    main()
