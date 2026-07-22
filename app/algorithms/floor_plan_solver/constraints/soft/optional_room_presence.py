from __future__ import annotations

from ...model import ModelContext
from ..base import ConstraintSettings, PenaltyTerm, require_room_types


class OptionalRoomPresenceConstraint:
    """Penalize omission of selected optional rooms without making them hard."""

    key = "optional_room_presence"

    def build_penalties(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> tuple[PenaltyTerm, ...]:
        target_types = require_room_types(
            settings.get("room_types", ()),
            "optional_room_presence.room_types",
        )
        penalties: list[PenaltyTerm] = []

        for variables in context.room_variables.values():
            if variables.room.required:
                continue
            if target_types and variables.room.room_type not in target_types:
                continue
            penalties.append(
                PenaltyTerm(
                    name=f"optional_room_absent:{variables.room.id_key}",
                    expression=1 - variables.present,
                )
            )

        return tuple(penalties)
