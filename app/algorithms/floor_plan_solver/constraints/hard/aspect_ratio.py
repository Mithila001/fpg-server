from __future__ import annotations

from collections.abc import Mapping

from ...exceptions import InvalidProfileError
from ...model import ModelContext
from ...preparation import normalize_room_type
from ..base import ConstraintSettings


class AspectRatioConstraint:
    key = "aspect_ratio"

    def apply(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> None:
        default_min = float(settings.get("min_ratio", 0.35))
        default_max = float(settings.get("max_ratio", 2.85))
        precision = int(settings.get("precision", 1000))
        if precision < 1:
            raise InvalidProfileError("aspect_ratio.precision must be positive")
        if default_min <= 0 or default_max < default_min:
            raise InvalidProfileError("Invalid default aspect-ratio range")

        hallway_types = {
            normalize_room_type(value)
            for value in tuple(
                settings.get("hallway_room_types", ("hallway",))
            )
        }
        excluded = {
            normalize_room_type(value)
            for value in tuple(settings.get("excluded_room_types", ()))
        }
        excluded_room_types = excluded | hallway_types

        raw_overrides = settings.get("overrides", {})
        overrides = raw_overrides if isinstance(raw_overrides, Mapping) else {}

        for variables in context.room_variables.values():
            room_type = variables.room.room_type_key
            if room_type in excluded_room_types:
                continue

            min_ratio = default_min
            max_ratio = default_max
            raw_override = overrides.get(room_type)
            if isinstance(raw_override, Mapping):
                min_ratio = float(raw_override.get("min_ratio", min_ratio))
                max_ratio = float(raw_override.get("max_ratio", max_ratio))

            if min_ratio <= 0 or max_ratio < min_ratio:
                raise InvalidProfileError(
                    f"Invalid aspect-ratio range for room type '{room_type}'"
                )

            min_scaled = int(round(min_ratio * precision))
            max_scaled = int(round(max_ratio * precision))
            context.model.Add(
                variables.width * precision >= variables.length * min_scaled
            ).OnlyEnforceIf(variables.present)
            context.model.Add(
                variables.width * precision <= variables.length * max_scaled
            ).OnlyEnforceIf(variables.present)
