from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from matplotlib.figure import Figure

from .config import RenderConfig
from .matplotlib_backend.renderer import close_figure

_UNSAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


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
        name: str | None = None,
    ) -> Path:
        """Save and always close a figure, including when export fails."""
        directory = self.root_directory / _safe_component(feature)
        if run_id is not None:
            directory /= _safe_component(run_id)
        directory.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        suffix = f"_{_safe_component(name)}" if name else ""
        path = directory / f"{timestamp}{suffix}_{uuid4().hex[:8]}.png"
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


def _safe_component(value: str) -> str:
    cleaned = _UNSAFE_COMPONENT.sub("_", value.strip()).strip("._")
    if not cleaned:
        raise ValueError("path component cannot be empty")
    return cleaned
