from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from ..config import RenderConfig


def create_figure(config: RenderConfig) -> tuple[Figure, Axes]:
    """Create an isolated, headless single-axis figure."""
    figure = Figure(
        figsize=(config.width_inches, config.height_inches),
        dpi=config.dpi,
        facecolor=config.background_color,
    )
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(1, 1, 1)
    axes.set_facecolor(config.background_color)
    return figure, axes


def create_figure_grid(
    config: RenderConfig,
    *,
    rows: int,
    columns: int,
    width_inches: float,
    height_inches: float,
) -> tuple[Figure, tuple[tuple[Axes, ...], ...]]:
    """Create an isolated, headless grid of axes without pyplot global state."""
    if rows <= 0 or columns <= 0:
        raise ValueError("rows and columns must be greater than zero")
    if width_inches <= 0 or height_inches <= 0:
        raise ValueError("figure dimensions must be greater than zero")

    figure = Figure(
        figsize=(width_inches, height_inches),
        dpi=config.dpi,
        facecolor=config.background_color,
    )
    FigureCanvasAgg(figure)

    axes_grid: list[tuple[Axes, ...]] = []
    for row_index in range(rows):
        row_axes: list[Axes] = []
        for column_index in range(columns):
            subplot_index = row_index * columns + column_index + 1
            axes = figure.add_subplot(rows, columns, subplot_index)
            axes.set_facecolor(config.background_color)
            row_axes.append(axes)
        axes_grid.append(tuple(row_axes))

    return figure, tuple(axes_grid)


def close_figure(figure: Figure) -> None:
    figure.clear()
