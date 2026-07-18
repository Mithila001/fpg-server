from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class VisualizationOutputManager:
    """Build predictable server-side output paths without mixing images into source code."""

    root_directory: Path

    @classmethod
    def from_environment(
        cls,
        *,
        environment_variable: str = "FPG_VISUALIZATION_DIR",
        default_directory: str | Path = "var/visualizations",
    ) -> "VisualizationOutputManager":
        configured = os.getenv(environment_variable)
        return cls(Path(configured) if configured else Path(default_directory))

    def build_path(
        self,
        *,
        stage: str,
        name: str,
        job_id: str | None = None,
        extension: str = "png",
    ) -> Path:
        safe_stage = _safe_component(stage)
        safe_name = _safe_component(name)
        safe_extension = extension.lower().lstrip(".")
        if not safe_extension:
            raise ValueError("extension cannot be empty")

        directory = self.root_directory
        if job_id is not None:
            directory = directory / _safe_component(job_id)
        directory = directory / safe_stage
        directory.mkdir(parents=True, exist_ok=True)

        return directory / f"{safe_name}.{safe_extension}"


def _safe_component(value: str) -> str:
    cleaned = _SAFE_COMPONENT.sub("_", value.strip()).strip("._")
    if not cleaned:
        raise ValueError("path component cannot be empty")
    return cleaned
