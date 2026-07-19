from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from ..config import RenderConfig


def create_figure(config: RenderConfig) -> tuple[Figure, Axes]:
    """Create an isolated, headless figure without pyplot global state."""
    figure = Figure(
        figsize=(config.width_inches, config.height_inches),
        dpi=config.dpi,
        facecolor=config.background_color,
    )
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(1, 1, 1)
    axes.set_facecolor(config.background_color)
    return figure, axes


def close_figure(figure: Figure) -> None:
    figure.clear()
