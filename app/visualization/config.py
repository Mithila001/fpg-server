from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.util.output_paths import get_output_root


@dataclass(frozen=True, slots=True)
class RenderConfig:
    """Package-wide figure and PNG export defaults."""

    width_inches: float = 10.0
    height_inches: float = 8.0
    dpi: int = 150
    background_color: str = "#ffffff"
    transparent: bool = False
    bbox_inches: str = "tight"
    output_root: Path = field(
        default_factory=lambda: get_output_root() / "visualizations"
    )

    def __post_init__(self) -> None:
        if self.width_inches <= 0 or self.height_inches <= 0:
            raise ValueError("figure dimensions must be greater than zero")
        if self.dpi <= 0:
            raise ValueError("dpi must be greater than zero")


DEFAULT_RENDER_CONFIG = RenderConfig()
