from __future__ import annotations

from pathlib import Path

from app.algorithms.floor_plan_scoring import score_floor_plan

from .builders import build_realistic_case
from .serialization import write_json

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "floor_plan_scoring_result.json"


def main() -> None:
    floor_plan, specification = build_realistic_case()
    result = score_floor_plan(floor_plan, specification)
    output_path = write_json(OUTPUT_FILE, result)

    print(f"Scoring completed: {result.total_score:.4f}/100")
    print(f"Critical gate passed: {result.passed_critical}")
    print(f"JSON output: {output_path}")


if __name__ == "__main__":
    main()
