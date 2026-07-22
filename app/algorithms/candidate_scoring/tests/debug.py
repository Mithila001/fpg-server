from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from enum import Enum
from time import perf_counter
from typing import Any, Mapping

from app.algorithms.candidate_scoring import (
    create_default_config,
    create_default_registry,
    evaluate_candidate,
)
from app.util.output_paths import create_artifact_path, create_run_directory

from .builders import build_scoring_input

def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: _to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set)):
        return [_to_jsonable(item) for item in value]
    return value


def main() -> None:
    scoring_input = build_scoring_input()
    started_at = perf_counter()
    result = evaluate_candidate(
        scoring_input,
        registry=create_default_registry(),
        config=create_default_config(),
    )
    elapsed_ms = (perf_counter() - started_at) * 1000.0

    report = {
        "elapsed_ms": elapsed_ms,
        "result": _to_jsonable(result),
    }
    output_directory = create_run_directory(
        "json", "candidate_scoring", "candidate-scoring-debug"
    )
    output_file = create_artifact_path(
        output_directory, "candidate-scoring-debug", "json"
    )
    output_file.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"Total score: {result.total_score:.3f}")
    print(f"Passed critical checks: {result.passed_critical_checks}")
    print(f"Evaluator count: {len(result.evaluator_results)}")
    print(f"Elapsed: {elapsed_ms:.3f} ms")
    print(f"Report written to: {output_file}")


if __name__ == "__main__":
    main()
