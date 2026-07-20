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
        filename_prefix: str | None = None,
    ) -> Path:
        """Save and always close a figure, including when export fails.

        Existing callers can keep using ``name`` and retain the historical
        ``<timestamp>_<name>_<id>.png`` format. Features that need a leading
        prefix can pass ``filename_prefix`` and receive
        ``<prefix>_<timestamp>_<id>.png``.
        """
        if name is not None and filename_prefix is not None:
            raise ValueError("use either name or filename_prefix, not both")

        directory = self.root_directory / _safe_component(feature)
        if run_id is not None:
            directory /= _safe_component(run_id)
        directory.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        unique_id = uuid4().hex[:8]

        if filename_prefix is not None:
            prefix = _safe_component(filename_prefix)
            filename = f"{prefix}_{timestamp}_{unique_id}.png"
        else:
            suffix = f"_{_safe_component(name)}" if name else ""
            filename = f"{timestamp}{suffix}_{unique_id}.png"

        path = directory / filename
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
