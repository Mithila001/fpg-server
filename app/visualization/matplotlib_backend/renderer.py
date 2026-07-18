from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence, cast

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.cm import ScalarMappable
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Circle, FancyArrowPatch, PathPatch, Polygon as MplPolygon
from matplotlib.path import Path as MplPath
from numpy.typing import ArrayLike

from ..config import GridStyle, RenderConfig
from ..geometry import Bounds, PointTuple


class MatplotlibRenderer:
    """Headless, instance-based Matplotlib renderer suitable for server-side image export."""

    def __init__(self, bounds: Bounds, config: RenderConfig) -> None:
        self.bounds = bounds
        self.config = config
        self.figure = Figure(
            figsize=(config.width_inches, config.height_inches),
            dpi=config.dpi,
            facecolor=config.background_color,
        )
        self.canvas = FigureCanvasAgg(self.figure)
        self.axes = self.figure.add_axes((0.04, 0.04, 0.92, 0.90))
        self.axes.set_facecolor(config.background_color)
        self.axes.set_xlim(bounds.left, bounds.right)
        self.axes.set_ylim(bounds.bottom, bounds.top)
        self.axes.set_aspect("equal", adjustable="box")

        if not config.show_axes:
            self.axes.set_axis_off()

        self._closed = False

    def draw_grid(self, style: GridStyle) -> None:
        if not style.visible:
            return

        minor_segments = self._grid_segments(style.minor_step)
        major_segments = self._grid_segments(style.major_step)

        if minor_segments:
            self.axes.add_collection(
                LineCollection(
                    minor_segments,
                    colors=style.minor_color,
                    linewidths=style.minor_line_width,
                    alpha=style.minor_alpha,
                    zorder=style.zorder,
                )
            )

        if major_segments:
            self.axes.add_collection(
                LineCollection(
                    major_segments,
                    colors=style.major_color,
                    linewidths=style.major_line_width,
                    alpha=style.major_alpha,
                    zorder=style.zorder + 0.01,
                )
            )

    def draw_polygon(
        self,
        points: Sequence[PointTuple],
        *,
        face_color: str,
        edge_color: str,
        alpha: float = 1.0,
        line_width: float = 1.0,
        zorder: float = 1.0,
        hatch: str | None = None,
    ) -> None:
        if len(points) < 3:
            raise ValueError("a polygon requires at least three points")

        patch = MplPolygon(
            points,
            closed=True,
            facecolor=face_color,
            edgecolor=edge_color,
            alpha=alpha,
            linewidth=line_width,
            zorder=zorder,
            hatch=hatch,
        )
        self.axes.add_patch(patch)

    def draw_polyline(
        self,
        points: Sequence[PointTuple],
        *,
        color: str,
        line_width: float = 1.0,
        alpha: float = 1.0,
        dashed: bool = False,
        zorder: float = 2.0,
    ) -> None:
        if len(points) < 2:
            raise ValueError("a polyline requires at least two points")

        xs, ys = zip(*points, strict=True)
        self.axes.plot(
            xs,
            ys,
            color=color,
            linewidth=line_width,
            alpha=alpha,
            linestyle="--" if dashed else "-",
            zorder=zorder,
        )

    def draw_segments(
        self,
        segments: Sequence[tuple[PointTuple, PointTuple]],
        *,
        color: str,
        line_width: float = 1.0,
        alpha: float = 1.0,
        zorder: float = 2.0,
    ) -> None:
        if not segments:
            return

        self.axes.add_collection(
            LineCollection(
                segments,
                colors=color,
                linewidths=line_width,
                alpha=alpha,
                zorder=zorder,
            )
        )

    def draw_points(
        self,
        points: Sequence[PointTuple],
        *,
        color: str,
        size: float = 36.0,
        edge_color: str = "#111827",
        line_width: float = 0.6,
        alpha: float = 1.0,
        zorder: float = 4.0,
    ) -> None:
        if not points:
            return

        xs, ys = zip(*points, strict=True)
        self.axes.scatter(
            xs,
            ys,
            c=color,
            s=size,
            edgecolors=edge_color,
            linewidths=line_width,
            alpha=alpha,
            zorder=zorder,
        )

    def draw_circle(
        self,
        center: PointTuple,
        radius: float,
        *,
        face_color: str,
        edge_color: str,
        alpha: float = 1.0,
        line_width: float = 1.0,
        zorder: float = 3.0,
    ) -> None:
        if radius <= 0:
            raise ValueError("circle radius must be greater than zero")

        self.axes.add_patch(
            Circle(
                center,
                radius,
                facecolor=face_color,
                edgecolor=edge_color,
                alpha=alpha,
                linewidth=line_width,
                zorder=zorder,
            )
        )

    def draw_text(
        self,
        position: PointTuple,
        text: str,
        *,
        color: str = "#111827",
        font_size: float = 9.0,
        horizontal_alignment: str = "center",
        vertical_alignment: str = "center",
        zorder: float = 6.0,
        background_color: str | None = None,
    ) -> None:
        box = None
        if background_color is not None:
            box = {
                "boxstyle": "round,pad=0.18",
                "facecolor": background_color,
                "edgecolor": "none",
                "alpha": 0.82,
            }

        self.axes.text(
            position[0],
            position[1],
            text,
            color=color,
            fontsize=font_size,
            ha=horizontal_alignment,
            va=vertical_alignment,
            zorder=zorder,
            bbox=box,
            clip_on=True,
        )

    def draw_arrow(
        self,
        start: PointTuple,
        end: PointTuple,
        *,
        color: str,
        line_width: float = 1.5,
        alpha: float = 1.0,
        zorder: float = 3.0,
    ) -> None:
        self.axes.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=10.0,
                color=color,
                linewidth=line_width,
                alpha=alpha,
                zorder=zorder,
                shrinkA=0.0,
                shrinkB=0.0,
            )
        )

    def draw_arc(
        self,
        center: PointTuple,
        width: float,
        height: float,
        theta_start: float,
        theta_end: float,
        *,
        color: str,
        line_width: float = 1.5,
        alpha: float = 1.0,
        zorder: float = 3.0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("arc width and height must be greater than zero")

        self.axes.add_patch(
            Arc(
                center,
                width=width,
                height=height,
                theta1=theta_start,
                theta2=theta_end,
                color=color,
                linewidth=line_width,
                alpha=alpha,
                zorder=zorder,
            )
        )

    def draw_quadratic_curve(
        self,
        start: PointTuple,
        control: PointTuple,
        end: PointTuple,
        *,
        color: str,
        line_width: float = 1.5,
        alpha: float = 1.0,
        zorder: float = 3.0,
    ) -> None:
        path = MplPath(
            vertices=[start, control, end],
            codes=[MplPath.MOVETO, MplPath.CURVE3, MplPath.CURVE3],
        )
        self.axes.add_patch(
            PathPatch(
                path,
                facecolor="none",
                edgecolor=color,
                linewidth=line_width,
                alpha=alpha,
                zorder=zorder,
            )
        )

    def draw_heatmap(
        self,
        values: ArrayLike,
        extent: Bounds,
        *,
        color_map: str = "viridis",
        alpha: float = 1.0,
        interpolation: str = "nearest",
        minimum_value: float | None = None,
        maximum_value: float | None = None,
        zorder: float = 0.5,
    ) -> object:
        array = np.asarray(values, dtype=float)
        if array.ndim != 2 or array.size == 0:
            raise ValueError("heatmap values must be a non-empty two-dimensional array")

        return self.axes.imshow(
            array,
            extent=(extent.left, extent.right, extent.bottom, extent.top),
            origin="lower",
            cmap=color_map,
            alpha=alpha,
            interpolation=interpolation,
            vmin=minimum_value,
            vmax=maximum_value,
            aspect="auto",
            zorder=zorder,
        )

    def add_colorbar(self, mappable: object, *, label: str | None = None) -> None:
        colorbar = self.figure.colorbar(
            cast(ScalarMappable, mappable),
            ax=self.axes,
            fraction=0.046,
            pad=0.04,
        )
        if label:
            colorbar.set_label(label)

    def set_title(self, title: str) -> None:
        self.axes.set_title(title, fontsize=12.0, pad=10.0)

    def save(self, output_path: Path) -> Path:
        if self._closed:
            raise RuntimeError("cannot save a closed renderer")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.canvas.draw()
        self.figure.savefig(
            path,
            dpi=self.config.dpi,
            facecolor=self.config.background_color,
            transparent=self.config.transparent,
        )
        return path

    def close(self) -> None:
        if self._closed:
            return
        self.figure.clear()
        self._closed = True

    def _grid_segments(self, step: float) -> list[tuple[PointTuple, PointTuple]]:
        x_positions = _positions(self.bounds.left, self.bounds.right, step)
        y_positions = _positions(self.bounds.bottom, self.bounds.top, step)

        vertical = [
            ((x, self.bounds.bottom), (x, self.bounds.top)) for x in x_positions
        ]
        horizontal = [
            ((self.bounds.left, y), (self.bounds.right, y)) for y in y_positions
        ]
        return vertical + horizontal


def create_matplotlib_renderer(bounds: Bounds, config: RenderConfig) -> MatplotlibRenderer:
    return MatplotlibRenderer(bounds=bounds, config=config)


def _positions(start: float, end: float, step: float) -> list[float]:
    first = math.ceil(start / step) * step
    last = math.floor(end / step) * step
    if first > last:
        return []

    count = int(round((last - first) / step)) + 1
    return [first + index * step for index in range(count)]
