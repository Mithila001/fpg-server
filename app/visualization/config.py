from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RenderConfig:
    """Image and world-canvas settings shared by all visualizations."""

    width_inches: float = 10.0
    height_inches: float = 8.0
    dpi: int = 120
    padding_units: float = 5.0
    background_color: str = "#ffffff"
    transparent: bool = False
    show_axes: bool = False

    def __post_init__(self) -> None:
        if self.width_inches <= 0:
            raise ValueError("width_inches must be greater than zero")
        if self.height_inches <= 0:
            raise ValueError("height_inches must be greater than zero")
        if self.dpi <= 0:
            raise ValueError("dpi must be greater than zero")
        if self.padding_units < 0:
            raise ValueError("padding_units cannot be negative")


@dataclass(frozen=True, slots=True)
class GridStyle:
    """Grid defaults follow the project scale: 10 units = 1 metre."""

    visible: bool = True
    minor_step: float = 10.0
    major_step: float = 50.0
    minor_color: str = "#e5e7eb"
    major_color: str = "#cbd5e1"
    minor_line_width: float = 0.45
    major_line_width: float = 0.9
    minor_alpha: float = 0.75
    major_alpha: float = 0.95
    zorder: float = 0.0

    def __post_init__(self) -> None:
        if self.minor_step <= 0:
            raise ValueError("minor_step must be greater than zero")
        if self.major_step <= 0:
            raise ValueError("major_step must be greater than zero")
        if self.minor_line_width < 0 or self.major_line_width < 0:
            raise ValueError("grid line widths cannot be negative")
