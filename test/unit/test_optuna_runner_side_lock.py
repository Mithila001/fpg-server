from __future__ import annotations

from app.algorithms.fpg_rooms.fpg_optuna.runner import (
    _effective_sampling_radius,
    _snap_search_bounds_to_grid,
)


def test_effective_sampling_radius_honors_cap_and_floor() -> None:
    assert _effective_sampling_radius(boundary_width=200.0, boundary_height=200.0) == 8.0
    assert _effective_sampling_radius(boundary_width=10.0, boundary_height=12.0) == 5.0
    assert _effective_sampling_radius(boundary_width=0.0, boundary_height=0.0) == 1.0


def test_snap_search_bounds_to_grid_snaps_inward() -> None:
    snapped_min, snapped_max = _snap_search_bounds_to_grid(
        min_value=7.0,
        max_value=97.0,
        grid_scale=10.0,
    )

    assert snapped_min == 10.0
    assert snapped_max == 90.0


def test_snap_search_bounds_to_grid_falls_back_when_window_too_small() -> None:
    snapped_min, snapped_max = _snap_search_bounds_to_grid(
        min_value=1.0,
        max_value=4.0,
        grid_scale=10.0,
    )

    assert snapped_min == 1.0
    assert snapped_max == 4.0
