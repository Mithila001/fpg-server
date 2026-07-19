from __future__ import annotations

import json
from pathlib import Path

from app.visualization.api import (
    CandidatePoint,
    CandidateSearchVisualization,
    SearchBounds,
    render_candidate_search,
)


def main() -> None:
    data_path = Path(__file__).with_name("mock_data.json")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    payload = CandidateSearchVisualization(
        trial_number=data["trial_number"],
        score=data["score"],
        points=tuple(CandidatePoint(**point) for point in data["points"]),
        bounds=SearchBounds(**data["bounds"]),
        grid_resolution=data["grid_resolution"],
        trial_count=data.get("trial_count"),
        metadata=data.get("metadata", {}),
    )
    output_path = render_candidate_search(payload, run_id="playground")
    print(f"Candidate Search PNG: {output_path}")


if __name__ == "__main__":
    main()
