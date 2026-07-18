from __future__ import annotations

import pytest

from ..geometry import Bounds, polygon_centroid


def test_bounds_from_points_and_padding() -> None:
    bounds = Bounds.from_points([(0, 0), (100, 80)])
    padded = bounds.padded(5)

    assert bounds.width == 100
    assert bounds.height == 80
    assert padded == Bounds(-5, -5, 105, 85)


def test_polygon_centroid_for_rectangle() -> None:
    centroid = polygon_centroid(((0, 0), (10, 0), (10, 20), (0, 20)))
    assert centroid == pytest.approx((5, 10))


def test_invalid_bounds_raise_value_error() -> None:
    with pytest.raises(ValueError):
        Bounds(0, 0, 0, 10)
