from __future__ import annotations

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

    flow_root = next((visualization_root / "flows").iterdir())
    assert {item.name for item in flow_root.iterdir()} == {"json", "png"}
    assert path.parent == flow_root / "png" / "candidate_search"
    assert path.name == "attempt-1-best-candidate.png"
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


def test_same_pipeline_run_reuses_one_visualization_folder(
    tmp_path: Path,
) -> None:
    visualization_root = tmp_path / "visualizations"
    manager = VisualizationOutputManager(visualization_root)
    config = RenderConfig(output_root=visualization_root)
    run_timestamp = "20260722T061530123456Z"

    first = manager.save_png(
        Figure(),
        feature="candidate_search",
        run_id="request-42",
        run_timestamp=run_timestamp,
        name="eligible-candidate-1",
        config=config,
    )
    second = manager.save_png(
        Figure(),
        feature="candidate_search",
        run_id="request-42",
        run_timestamp=run_timestamp,
        name="eligible-candidate-2",
        config=config,
    )

    assert first.parent == second.parent
    assert len(tuple(first.parent.glob("*.png"))) == 2
