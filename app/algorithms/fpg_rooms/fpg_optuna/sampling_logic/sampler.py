from __future__ import annotations

import math
from typing import Any

import optuna
from optuna.distributions import FloatDistribution

from app.core.fpg_rooms.config_fpg import OPTUNA_SEARCH_SPACE_GRID_SCALE
from .policy import RoomSamplingContext, RoomSamplingPolicy


def _snap_bounds_to_grid(
    low: float,
    high: float,
    grid_scale: float,
) -> tuple[float, float]:
    """Snap narrowed bounds to the nearest grid alignment."""
    step = max(1.0, float(grid_scale))
    snapped_low = ((float(low) + step - 1e-9) // step) * step
    snapped_high = (float(high) // step) * step

    if snapped_low > snapped_high:
        return float(low), float(high)

    return float(snapped_low), float(snapped_high)


class RoomAwareTPESampler(optuna.samplers.TPESampler):
    def __init__(self, policy: RoomSamplingPolicy | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.policy = policy or RoomSamplingPolicy()

    def sample_independent(
        self,
        study: optuna.study.Study,
        trial: optuna.trial.FrozenTrial,
        param_name: str,
        param_distribution: optuna.distributions.BaseDistribution,
    ) -> Any:
        if not param_name.endswith("_y"):
            return super().sample_independent(
                study, trial, param_name, param_distribution
            )

        context_data = trial.user_attrs.get("fpg_current_room_context")
        if not isinstance(context_data, dict):
            return super().sample_independent(
                study, trial, param_name, param_distribution
            )

        try:
            context = RoomSamplingContext(
                room_id=str(context_data["room_id"]),
                room_name=str(context_data["room_name"]),
                room_type=str(context_data["room_type"]),
                radius=float(context_data["radius"]),
                floor_width=float(context_data["floor_width"]),
                floor_height=float(context_data["floor_height"]),
            )
        except (KeyError, TypeError, ValueError):
            return super().sample_independent(
                study, trial, param_name, param_distribution
            )

        sampled_positions = trial.user_attrs.get("fpg_sampled_positions", {})
        if not isinstance(sampled_positions, dict):
            sampled_positions = {}

        low, high = self.policy.get_y_bounds(context, sampled_positions)

        if isinstance(param_distribution, FloatDistribution):
            base_low = float(param_distribution.low)
            base_high = float(param_distribution.high)

            if not math.isfinite(low) or not math.isfinite(high):
                return super().sample_independent(
                    study, trial, param_name, param_distribution
                )

            narrowed_low = max(base_low, float(low))
            narrowed_high = min(base_high, float(high))

            if narrowed_low > narrowed_high:
                narrowed_low = base_low
                narrowed_high = base_high

            if narrowed_low == narrowed_high:
                return narrowed_low

            narrowed_low, narrowed_high = _snap_bounds_to_grid(
                narrowed_low, narrowed_high, OPTUNA_SEARCH_SPACE_GRID_SCALE
            )

            narrowed = FloatDistribution(
                low=narrowed_low,
                high=narrowed_high,
                step=param_distribution.step,
                log=param_distribution.log,
            )
            return super().sample_independent(study, trial, param_name, narrowed)

        return super().sample_independent(study, trial, param_name, param_distribution)
