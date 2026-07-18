from __future__ import annotations

from dataclasses import dataclass

from .geometry import PointTuple


@dataclass(frozen=True, slots=True)
class PointMarker:
    x: float
    y: float
    label: str | None = None
    value: float | None = None
    color: str | None = None
    size: float = 42.0
    radius_units: float | None = None

    @property
    def point(self) -> PointTuple:
        return (self.x, self.y)


@dataclass(frozen=True, slots=True)
class ZoneOverlay:
    points: tuple[PointTuple, ...]
    label: str | None = None
    face_color: str = "#93c5fd"
    edge_color: str = "#2563eb"
    alpha: float = 0.22
    line_width: float = 1.2


@dataclass(frozen=True, slots=True)
class PathOverlay:
    points: tuple[PointTuple, ...]
    label: str | None = None
    color: str = "#dc2626"
    line_width: float = 2.0
    dashed: bool = False
    arrow_at_end: bool = False


@dataclass(frozen=True, slots=True)
class GraphNode:
    id: str
    x: float
    y: float
    label: str | None = None
    value: float | None = None
    color: str | None = None
    radius_units: float | None = None

    @property
    def point(self) -> PointTuple:
        return (self.x, self.y)


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source_id: str
    target_id: str
    label: str | None = None
    directed: bool = False
    highlighted: bool = False
    color: str | None = None
    line_width: float | None = None
