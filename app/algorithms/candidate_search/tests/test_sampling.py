from __future__ import annotations

from decimal import Decimal

from ..models import CandidatePoint
from ..optimizer import search_candidates
from .builders import (
    build_candidate_search_input,
    build_candidate_settings,
    build_candidate_targets,
    build_recording_evaluator,
)


def test_every_trial_samples_one_valid_point_for_every_target() -> None:
    targets = build_candidate_targets(
        ("living_room_1", "bedroom_1", "bedroom_2", "kitchen_1")
    )
    settings = build_candidate_settings(
        min_x=-7.5,
        max_x=23.4,
        min_y=2.5,
        max_y=31.1,
        grid_resolution=2.5,
        trial_count=15,
    )
    evaluator = build_recording_evaluator()
    search_input = build_candidate_search_input(
        targets=targets,
        settings=settings,
        evaluator=evaluator,
    )

    search_candidates(search_input)

    expected_room_ids = tuple(target.room_id for target in targets)

    for sampled_points in evaluator.calls:
        assert isinstance(sampled_points, tuple)
        assert len(sampled_points) == len(targets)
        assert all(isinstance(point, CandidatePoint) for point in sampled_points)
        assert tuple(point.room_id for point in sampled_points) == expected_room_ids

        for point in sampled_points:
            assert settings.min_x <= point.x <= settings.max_x
            assert settings.min_y <= point.y <= settings.max_y
            assert _is_on_grid(
                value=point.x,
                minimum=settings.min_x,
                resolution=settings.grid_resolution,
            )
            assert _is_on_grid(
                value=point.y,
                minimum=settings.min_y,
                resolution=settings.grid_resolution,
            )


def test_sampling_never_steps_past_a_non_divisible_upper_bound() -> None:
    settings = build_candidate_settings(
        min_x=0.0,
        max_x=10.9,
        min_y=0.0,
        max_y=7.9,
        grid_resolution=3.0,
        trial_count=20,
    )
    evaluator = build_recording_evaluator()

    search_candidates(
        build_candidate_search_input(settings=settings, evaluator=evaluator)
    )

    for sampled_points in evaluator.calls:
        for point in sampled_points:
            assert point.x in {0.0, 3.0, 6.0, 9.0}
            assert point.y in {0.0, 3.0, 6.0}


def test_fixed_axis_ranges_always_return_the_fixed_coordinate() -> None:
    settings = build_candidate_settings(
        min_x=25.0,
        max_x=25.0,
        min_y=-10.0,
        max_y=-10.0,
        grid_resolution=5.0,
        trial_count=6,
    )
    evaluator = build_recording_evaluator()

    result = search_candidates(
        build_candidate_search_input(settings=settings, evaluator=evaluator)
    )

    assert all(
        point.x == 25.0 and point.y == -10.0
        for sampled_points in evaluator.calls
        for point in sampled_points
    )
    assert all(point.x == 25.0 and point.y == -10.0 for point in result.points)


def test_same_seed_produces_the_same_trial_samples_and_result() -> None:
    first_evaluator = build_recording_evaluator()
    second_evaluator = build_recording_evaluator()
    settings = build_candidate_settings(trial_count=18, random_seed=441)

    first_result = search_candidates(
        build_candidate_search_input(
            settings=settings,
            evaluator=first_evaluator,
        )
    )
    second_result = search_candidates(
        build_candidate_search_input(
            settings=settings,
            evaluator=second_evaluator,
        )
    )

    assert first_evaluator.calls == second_evaluator.calls
    assert first_evaluator.scores == second_evaluator.scores
    assert first_result == second_result


def _is_on_grid(
    *,
    value: float,
    minimum: float,
    resolution: float,
) -> bool:
    offset = Decimal(str(value)) - Decimal(str(minimum))
    grid_resolution = Decimal(str(resolution))

    return offset % grid_resolution == 0
