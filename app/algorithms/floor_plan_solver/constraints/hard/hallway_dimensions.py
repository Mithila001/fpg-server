from __future__ import annotations

from ...exceptions import InvalidProfileError
from ...model import ModelContext
from ...preparation import normalize_room_type
from ..base import ConstraintSettings


class HallwayDimensionsConstraint:
    """Keep one hallway dimension within the configured corridor-width range."""

    key = "hallway_dimensions"

    def apply(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> None:
        hallway_types = {
            normalize_room_type(value)
            for value in tuple(
                settings.get("hallway_room_types", ("hallway",))
            )
        }
        minimum_width = int(settings.get("minimum_width", 8))
        maximum_width = int(settings.get("maximum_width", 10))

        if minimum_width <= 0:
            raise InvalidProfileError(
                "hallway_dimensions.minimum_width must be positive"
            )
        if maximum_width < minimum_width:
            raise InvalidProfileError(
                "hallway_dimensions.maximum_width must be greater than or "
                "equal to minimum_width"
            )

        for variables in context.room_variables.values():
            if variables.room.room_type_key not in hallway_types:
                continue

            horizontal = context.model.NewBoolVar(
                context.new_name(
                    "hallway_horizontal",
                    variables.room.id_key,
                )
            )
            vertical = context.model.NewBoolVar(
                context.new_name(
                    "hallway_vertical",
                    variables.room.id_key,
                )
            )

            # A present hallway chooses exactly one orientation. An absent
            # optional hallway chooses neither orientation.
            context.model.Add(horizontal + vertical == variables.present)

            # Horizontal hallway: height is the corridor width; room width may
            # extend as far as its prepared room-size bounds allow.
            context.model.Add(
                variables.height >= minimum_width
            ).OnlyEnforceIf(horizontal)
            context.model.Add(
                variables.height <= maximum_width
            ).OnlyEnforceIf(horizontal)

            # Vertical hallway: width is the corridor width; room height may
            # extend as far as its prepared room-size bounds allow.
            context.model.Add(
                variables.width >= minimum_width
            ).OnlyEnforceIf(vertical)
            context.model.Add(
                variables.width <= maximum_width
            ).OnlyEnforceIf(vertical)
