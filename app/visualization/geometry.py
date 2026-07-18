from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Sequence

PointTuple = tuple[float, float]


@dataclass(frozen=True, slots=True)
class Bounds:
    left: float
    bottom: float
    right: float
    top: float

    def __post_init__(self) -> None:
        values = (self.left, self.bottom, self.right, self.top)
        if not all(isfinite(value) for value in values):
            raise ValueError("bounds values must be finite")
        if self.right <= self.left:
            raise ValueError("right must be greater than left")
        if self.top <= self.bottom:
            raise ValueError("top must be greater than bottom")

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top - self.bottom

    @property
    def center(self) -> PointTuple:
        return ((self.left + self.right) / 2.0, (self.bottom + self.top) / 2.0)

    def padded(self, amount: float) -> "Bounds":
        if amount < 0:
            raise ValueError("padding amount cannot be negative")
        return Bounds(
            left=self.left - amount,
            bottom=self.bottom - amount,
            right=self.right + amount,
            top=self.top + amount,
        )

    @classmethod
    def from_points(cls, points: Iterable[PointTuple]) -> "Bounds":
        materialized = list(points)
        if not materialized:
            raise ValueError("at least one point is required to calculate bounds")

        xs = [point[0] for point in materialized]
        ys = [point[1] for point in materialized]
        left = min(xs)
        right = max(xs)
        bottom = min(ys)
        top = max(ys)

        # A single point or a perfectly horizontal/vertical input still needs
        # a valid drawable world area.
        if left == right:
            left -= 0.5
            right += 0.5
        if bottom == top:
            bottom -= 0.5
            top += 0.5

        return cls(left=left, bottom=bottom, right=right, top=top)


def polygon_centroid(points: Sequence[PointTuple]) -> PointTuple:
    """Return the area centroid, with a safe average fallback for degenerate polygons."""

    if not points:
        raise ValueError("polygon centroid requires at least one point")

    if len(points) < 3:
        return _average_point(points)

    doubled_area = 0.0
    centroid_x = 0.0
    centroid_y = 0.0

    for index, current in enumerate(points):
        following = points[(index + 1) % len(points)]
        cross = current[0] * following[1] - following[0] * current[1]
        doubled_area += cross
        centroid_x += (current[0] + following[0]) * cross
        centroid_y += (current[1] + following[1]) * cross

    if abs(doubled_area) < 1e-12:
        return _average_point(points)

    scale = 1.0 / (3.0 * doubled_area)
    return (centroid_x * scale, centroid_y * scale)


def midpoint(start: PointTuple, end: PointTuple) -> PointTuple:
    return ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)


def _average_point(points: Sequence[PointTuple]) -> PointTuple:
    count = len(points)
    return (
        sum(point[0] for point in points) / count,
        sum(point[1] for point in points) / count,
    )
