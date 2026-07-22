from __future__ import annotations

import re
from pathlib import Path

import pytest
from matplotlib.figure import Figure

from app.visualization.config import RenderConfig
from app.visualization.output_manager import VisualizationOutputManager


def test_png_is_saved_under_timestamped_feature_run(tmp_path: Path) -> None:
    visualization_root = tmp_path / "visualizations"
    manager = VisualizationOutputManager(visualization_root)
    run_timestamp = "20260722T061530123456Z"

    path = manager.save_png(
        Figure(),
        feature="candidate_search",
        run_id="request-42",
        run_timestamp=run_timestamp,
        name="attempt-1-best-candidate",
        config=RenderConfig(output_root=visualization_root),
    )

    assert path.parent == (
        visualization_root
        / "candidate_search"
        / "20260722T061530123456Z_request-42"
    )
    assert re.fullmatch(
        r"\d{8}T\d{12}Z_attempt-1-best-candidate_[a-f0-9]{8}\.png",
        path.name,
    )
    assert path.is_file()


def test_figure_is_cleared_when_png_export_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    figure = Figure()
    figure.add_subplot(1, 1, 1)
    manager = VisualizationOutputManager(tmp_path / "visualizations")
    monkeypatch.setattr(
        figure,
        "savefig",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    with pytest.raises(OSError, match="disk full"):
        manager.save_png(
            figure,
            feature="candidate_search",
            run_id="request-42",
            config=RenderConfig(output_root=tmp_path / "visualizations"),
        )

    assert figure.axes == []
