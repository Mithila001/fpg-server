from __future__ import annotations

import json
from time import perf_counter

from app.util.output_paths import create_artifact_path, create_run_directory

from ..models import CandidatePoint
from ..optimizer import search_candidates
from .builders import (
    build_candidate_search_input,
    build_candidate_settings,
    build_candidate_targets,
    build_recording_evaluator,
)

def main() -> None:
    evaluator = build_recording_evaluator()
    search_input = build_candidate_search_input(
        targets=build_candidate_targets(
            ("living_room_1", "bedroom_1", "bedroom_2", "kitchen_1")
        ),
        settings=build_candidate_settings(
            min_x=0.0,
            max_x=120.0,
            min_y=0.0,
            max_y=90.0,
            grid_resolution=5.0,
            trial_count=30,
            random_seed=2026,
        ),
        evaluator=evaluator,
    )

    started_at = perf_counter()
    result = search_candidates(search_input)
    elapsed_seconds = perf_counter() - started_at

    report = {
        "settings": {
            "min_x": search_input.settings.min_x,
            "max_x": search_input.settings.max_x,
            "min_y": search_input.settings.min_y,
            "max_y": search_input.settings.max_y,
            "grid_resolution": search_input.settings.grid_resolution,
            "trial_count": search_input.settings.trial_count,
            "random_seed": search_input.settings.random_seed,
        },
        "target_room_ids": [target.room_id for target in search_input.targets],
        "elapsed_seconds": elapsed_seconds,
        "completed_trials": result.completed_trials,
        "best_score": result.score,
        "best_points": [_point_payload(point) for point in result.points],
        "trials": [
            {
                "trial_number": trial_index + 1,
                "score": evaluator.scores[trial_index],
                "points": [_point_payload(point) for point in points],
            }
            for trial_index, points in enumerate(evaluator.calls)
        ],
    }

    output_directory = create_run_directory(
        "json", "candidate_search", "candidate-search-debug"
    )
    output_file = create_artifact_path(
        output_directory, "candidate-search-debug", "json"
    )
    output_file.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"Completed trials: {result.completed_trials}")
    print(f"Best score: {result.score}")
    print(f"Elapsed seconds: {elapsed_seconds:.6f}")
    print("Best candidate points:")

    for point in result.points:
        print(f"  {point.room_id}: ({point.x}, {point.y})")

    print(f"Debug report: {output_file}")


def _point_payload(point: CandidatePoint) -> dict[str, object]:
    return {
        "room_id": point.room_id,
        "x": point.x,
        "y": point.y,
    }


if __name__ == "__main__":
    main()
