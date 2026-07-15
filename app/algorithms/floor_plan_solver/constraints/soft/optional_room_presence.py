from __future__ import annotations

from ...model import ModelContext
from ...preparation import normalize_room_type
from ..base import ConstraintSettings, PenaltyTerm


class OptionalRoomPresenceConstraint:
    """Penalize omission of selected optional rooms without making them hard."""

    key = "optional_room_presence"

    def build_penalties(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> tuple[PenaltyTerm, ...]:
        raw_types = tuple(settings.get("room_types", ()))
        target_types = {normalize_room_type(value) for value in raw_types}
        penalties: list[PenaltyTerm] = []

        for variables in context.room_variables.values():
            if variables.room.required:
                continue
            if target_types and variables.room.room_type_key not in target_types:
                continue
            penalties.append(
                PenaltyTerm(
                    name=f"optional_room_absent:{variables.room.id_key}",
                    expression=1 - variables.present,
                )
            )

        return tuple(penalties)
