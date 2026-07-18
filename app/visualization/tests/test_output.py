from __future__ import annotations

from ..output import VisualizationOutputManager


def test_output_manager_builds_job_and_stage_path(tmp_path) -> None:
    manager = VisualizationOutputManager(tmp_path)

    path = manager.build_path(
        job_id="job 42",
        stage="candidate scoring",
        name="trial:001",
    )

    assert path == tmp_path / "job_42" / "candidate_scoring" / "trial_001.png"
    assert path.parent.is_dir()
