from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from optuna.distributions import FloatDistribution

from app.algorithms.fpg_rooms.fpg_optuna.sampling_logic import (
    RoomSamplingContext,
    RoomSamplingPolicy,
)
from app.algorithms.fpg_rooms.fpg_optuna.sampling_logic.sampler import (
    RoomAwareTPESampler,
)


def test_front_rooms_stay_in_bottom_half() -> None:
    policy = RoomSamplingPolicy()
    context = RoomSamplingContext(
        room_id="room_0",
        room_name="veranda1",
        room_type="veranda",
        radius=15.2,
        floor_width=100.0,
        floor_height=150.0,
    )

    low, high = policy.get_y_bounds(context, {})

    assert low == 15.2
    assert high == 75.0


def test_back_rooms_stay_near_back_boundary() -> None:
    policy = RoomSamplingPolicy()
    context = RoomSamplingContext(
        room_id="room_1",
        room_name="bathroom1",
        room_type="bathroom",
        radius=12.0,
        floor_width=100.0,
        floor_height=150.0,
    )

    low, high = policy.get_y_bounds(context, {})

    assert high == 138.0
    assert low >= 126.0
    assert low <= high


def test_private_rooms_stay_in_top_half() -> None:
    policy = RoomSamplingPolicy()
    context = RoomSamplingContext(
        room_id="room_4",
        room_name="attachedBathroom1",
        room_type="attachedBathroom",
        radius=12.0,
        floor_width=100.0,
        floor_height=150.0,
    )

    low, high = policy.get_y_bounds(context, {})

    assert low >= 75.0
    assert high <= 138.0


def test_front_overrides_private_for_overlap_type() -> None:
    policy = RoomSamplingPolicy()
    context = RoomSamplingContext(
        room_id="room_5",
        room_name="garage1",
        room_type="garage",
        radius=12.0,
        floor_width=100.0,
        floor_height=150.0,
    )

    low, high = policy.get_y_bounds(context, {})

    assert low == 12.0
    assert high == 75.0


def test_living_room_tracks_veranda_proximity() -> None:
    policy = RoomSamplingPolicy()
    context = RoomSamplingContext(
        room_id="room_2",
        room_name="livingRoom1",
        room_type="livingRoom",
        radius=20.0,
        floor_width=100.0,
        floor_height=150.0,
    )
    sampled_positions = {
        "room_0": {
            "type": "veranda",
            "x": 10.0,
            "y": 15.2,
            "radius": 15.2,
        }
    }

    low, high = policy.get_y_bounds(context, sampled_positions)

    assert low >= 20.0
    assert high <= 60.4001


def test_kitchen_tracks_dining_room_proximity_and_back_bias() -> None:
    policy = RoomSamplingPolicy()
    context = RoomSamplingContext(
        room_id="room_3",
        room_name="kitchen1",
        room_type="kitchen",
        radius=12.0,
        floor_width=100.0,
        floor_height=150.0,
    )
    sampled_positions = {
        "room_2": {
            "type": "diningRoom",
            "x": 40.0,
            "y": 100.0,
            "radius": 18.0,
        }
    }

    low, high = policy.get_y_bounds(context, sampled_positions)

    assert low >= 126.0
    assert high <= 138.0
    assert low <= high


def test_sampling_order_prioritizes_front_rooms_first() -> None:
    policy = RoomSamplingPolicy()
    nodes = [
        SimpleNamespace(id="room_3", room_type="bathroom"),
        SimpleNamespace(id="room_1", room_type="livingRoom"),
        SimpleNamespace(id="room_2", room_type="kitchen"),
        SimpleNamespace(id="room_0", room_type="veranda"),
        SimpleNamespace(id="room_4", room_type="diningRoom"),
    ]

    ordered = policy.sort_nodes_for_sampling(nodes)

    assert [node.room_type for node in ordered] == [
        "veranda",
        "livingRoom",
        "diningRoom",
        "kitchen",
        "bathroom",
    ]


def test_back_room_uses_back_band_when_proximity_band_does_not_overlap() -> None:
    policy = RoomSamplingPolicy()
    context = RoomSamplingContext(
        room_id="room_3",
        room_name="kitchen1",
        room_type="kitchen",
        radius=12.0,
        floor_width=100.0,
        floor_height=150.0,
    )
    sampled_positions = {
        "room_2": {
            "type": "diningRoom",
            "x": 40.0,
            "y": 20.0,
            "radius": 18.0,
        }
    }

    low, high = policy.get_y_bounds(context, sampled_positions)

    assert low == 126.0
    assert high == 138.0


def test_sampler_returns_deterministic_value_for_collapsed_range() -> None:
    sampler = RoomAwareTPESampler()

    value = sampler.sample_independent(
        study=cast(Any, SimpleNamespace()),
        trial=cast(
            Any,
            SimpleNamespace(
                user_attrs={
                    "fpg_current_room_context": {
                        "room_id": "room_0",
                        "room_name": "veranda1",
                        "room_type": "veranda",
                        "radius": 15.0,
                        "floor_width": 100.0,
                        "floor_height": 30.0,
                    },
                    "fpg_sampled_positions": {},
                }
            ),
        ),
        param_name="room_0_y",
        param_distribution=FloatDistribution(low=15.0, high=15.0),
    )

    assert value == 15.0
