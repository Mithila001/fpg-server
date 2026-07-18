from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol, Sequence

from numpy.typing import ArrayLike

from .config import GridStyle, RenderConfig
from .geometry import Bounds, PointTuple


class DrawingRenderer(Protocol):
    bounds: Bounds

    def draw_grid(self, style: GridStyle) -> None: ...

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
    ) -> None: ...

    def draw_polyline(
        self,
        points: Sequence[PointTuple],
        *,
        color: str,
        line_width: float = 1.0,
        alpha: float = 1.0,
        dashed: bool = False,
        zorder: float = 2.0,
    ) -> None: ...

    def draw_segments(
        self,
        segments: Sequence[tuple[PointTuple, PointTuple]],
        *,
        color: str,
        line_width: float = 1.0,
        alpha: float = 1.0,
        zorder: float = 2.0,
    ) -> None: ...

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
    ) -> None: ...

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
    ) -> None: ...

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
    ) -> None: ...

    def draw_arrow(
        self,
        start: PointTuple,
        end: PointTuple,
        *,
        color: str,
        line_width: float = 1.5,
        alpha: float = 1.0,
        zorder: float = 3.0,
    ) -> None: ...

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
    ) -> None: ...

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
    ) -> None: ...

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
    ) -> object: ...

    def add_colorbar(self, mappable: object, *, label: str | None = None) -> None: ...

    def set_title(self, title: str) -> None: ...

    def save(self, output_path: Path) -> Path: ...

    def close(self) -> None: ...


RendererFactory = Callable[[Bounds, RenderConfig], DrawingRenderer]
