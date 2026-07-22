from __future__ import annotations

from ...model import ModelContext
from ...preparation import normalize_room_type
from ..base import ConstraintSettings, PenaltyTerm
from ..geometry import active_linear_penalty


class BathroomDepthConstraint:
    """Prefer bathrooms farther from the front boundary (y = 0)."""

    key = "bathroom_depth"

    def build_penalties(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> tuple[PenaltyTerm, ...]:
        target_types = {
            normalize_room_type(value)
            for value in tuple(
                settings.get(
                    "room_types", ("bathroom", "attached_bathroom")
                )
            )
        }
        floor = context.problem.floor
        penalties: list[PenaltyTerm] = []

        for variables in context.room_variables.values():
            if variables.room.room_type_key not in target_types:
                continue
            expression = 2 * floor.length - (2 * variables.y + variables.length)
            penalty = active_linear_penalty(
                context,
                expression,
                2 * floor.length,
                variables.present,
                f"bathroom_depth_penalty_{variables.room.id_key}",
            )
            penalties.append(
                PenaltyTerm(
                    name=f"bathroom_depth:{variables.room.id_key}",
                    expression=penalty,
                )
            )

        return tuple(penalties)
