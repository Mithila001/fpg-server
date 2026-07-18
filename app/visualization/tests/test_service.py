from __future__ import annotations

from ..api import VisualizationService
from ..output import VisualizationOutputManager
from .builders import build_floor_plan


def test_visualization_service_uses_job_and_stage_output_structure(tmp_path) -> None:
    service = VisualizationService(
        output_manager=VisualizationOutputManager(tmp_path),
    )

    output = service.render_floor_plan(
        build_floor_plan(),
        job_id="job-001",
        stage="solver",
        name="initial-layout",
    )

    assert output == tmp_path / "job-001" / "solver" / "initial-layout.png"
    assert output.is_file()
