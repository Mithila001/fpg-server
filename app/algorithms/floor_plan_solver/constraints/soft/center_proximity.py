from __future__ import annotations

from ...exceptions import InvalidProfileError
from ...model import ModelContext
from ..base import ConstraintSettings, PenaltyTerm, require_room_types
from ..geometry import active_linear_penalty


class CenterProximityConstraint:
    """Prefer horizontal centering with an optional bias toward the front."""

    key = "center_proximity"

    def build_penalties(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> tuple[PenaltyTerm, ...]:
        front_bias = int(settings.get("front_bias", 1))
        if front_bias < 0:
            raise InvalidProfileError("center_proximity.front_bias cannot be negative")
        excluded = require_room_types(
            settings.get("excluded_room_types", ()),
            "center_proximity.excluded_room_types",
        )

        floor = context.problem.floor
        penalties: list[PenaltyTerm] = []
        for variables in context.room_variables.values():
            if variables.room.room_type in excluded:
                continue

            center_delta = context.model.NewIntVar(
                -floor.width,
                floor.width,
                context.new_name("center_delta", variables.room.id_key),
            )
            context.model.Add(
                center_delta == 2 * variables.x + variables.width - floor.width
            )
            horizontal_distance = context.model.NewIntVar(
                0,
                floor.width,
                context.new_name("center_distance", variables.room.id_key),
            )
            context.model.AddAbsEquality(horizontal_distance, center_delta)

            expression = horizontal_distance + front_bias * variables.y
            upper_bound = floor.width + front_bias * floor.length
            penalty = active_linear_penalty(
                context,
                expression,
                upper_bound,
                variables.present,
                f"center_penalty_{variables.room.id_key}",
            )
            penalties.append(
                PenaltyTerm(
                    name=f"center_proximity:{variables.room.id_key}",
                    expression=penalty,
                )
            )

        return tuple(penalties)
