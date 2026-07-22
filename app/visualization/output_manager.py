from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from matplotlib.figure import Figure

from app.util.output_paths import (
    create_artifact_path,
    create_timestamped_directory,
    safe_path_component,
)

from .config import RenderConfig
from .matplotlib_backend.renderer import close_figure


@dataclass(frozen=True, slots=True)
class VisualizationOutputManager:
    root_directory: Path

    def save_png(
        self,
        figure: Figure,
        *,
        feature: str,
        config: RenderConfig,
        run_id: str | None = None,
        run_timestamp: str | None = None,
        name: str | None = None,
        filename_prefix: str | None = None,
    ) -> Path:
        """Save and always close a figure, including when export fails.

        ``name`` and ``filename_prefix`` are retained as caller-friendly aliases;
        every artifact now follows ``<timestamp>_<description>_<id>.png``.
        """
        if name is not None and filename_prefix is not None:
            raise ValueError("use either name or filename_prefix, not both")

        directory = create_timestamped_directory(
            self.root_directory / safe_path_component(feature),
            run_id or feature,
            run_timestamp=run_timestamp,
        )
        path = create_artifact_path(
            directory,
            filename_prefix or name or feature,
            "png",
        )
        try:
            figure.savefig(
                path,
                dpi=config.dpi,
                facecolor=config.background_color,
                transparent=config.transparent,
                bbox_inches=config.bbox_inches,
            )
            return path.resolve()
        finally:
            close_figure(figure)
