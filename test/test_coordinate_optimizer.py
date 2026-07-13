from __future__ import annotations

import pytest

from app.algorithms.candidate_search import (
    Coordinate,
    CoordinateOptimizationSettings,
    CoordinateTarget,
    optimize_coordinates,
)


def test_optimize_coordinates_returns_grid_aligned_result() -> None:
    targets = [
        CoordinateTarget(label="living_room"),
        CoordinateTarget(label="kitchen"),
    ]

    settings = CoordinateOptimizationSettings(
        min_x=0,
        max_x=10,
        min_y=0,
        max_y=10,
        grid_resolution=5,
        trial_count=5,
    )

    def evaluator(coordinates: tuple[Coordinate, ...]) -> float:
        return sum(point.x + point.y for point in coordinates)

    result = optimize_coordinates(
        targets=targets,
        settings=settings,
        evaluator=evaluator,
    )

    assert [point.label for point in result.coordinates] == [
        "living_room",
        "kitchen",
    ]

    for point in result.coordinates:
        assert point.x in {0.0, 5.0, 10.0}
        assert point.y in {0.0, 5.0, 10.0}

    assert result.score == evaluator(result.coordinates)


def test_fixed_bounds_produce_fixed_coordinates() -> None:
    targets = [
        CoordinateTarget(label="bedroom"),
    ]

    settings = CoordinateOptimizationSettings(
        min_x=12,
        max_x=12,
        min_y=8,
        max_y=8,
        grid_resolution=2,
        trial_count=2,
    )

    result = optimize_coordinates(
        targets=targets,
        settings=settings,
        evaluator=lambda coordinates: 100.0,
    )

    assert result.coordinates == (
        Coordinate(
            label="bedroom",
            x=12.0,
            y=8.0,
        ),
    )

    assert result.score == 100.0


def test_duplicate_labels_are_rejected() -> None:
    targets = [
        CoordinateTarget(label="bedroom"),
        CoordinateTarget(label="bedroom"),
    ]

    settings = CoordinateOptimizationSettings(
        min_x=0,
        max_x=10,
        min_y=0,
        max_y=10,
        grid_resolution=1,
        trial_count=2,
    )

    with pytest.raises(ValueError, match="labels must be unique"):
        optimize_coordinates(
            targets=targets,
            settings=settings,
            evaluator=lambda coordinates: 1.0,
        )


def test_invalid_grid_resolution_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="grid_resolution must be greater than zero",
    ):
        CoordinateOptimizationSettings(
            min_x=0,
            max_x=10,
            min_y=0,
            max_y=10,
            grid_resolution=0,
            trial_count=2,
        )


def test_non_numeric_evaluator_result_is_rejected() -> None:
    targets = [
        CoordinateTarget(label="living_room"),
    ]

    settings = CoordinateOptimizationSettings(
        min_x=0,
        max_x=10,
        min_y=0,
        max_y=10,
        grid_resolution=5,
        trial_count=1,
    )

    with pytest.raises(
        TypeError,
        match="must return a numeric score",
    ):
        optimize_coordinates(
            targets=targets,
            settings=settings,
            evaluator=lambda coordinates: "invalid",  # type: ignore[return-value]
        )
