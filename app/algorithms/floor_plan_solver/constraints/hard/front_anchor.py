from __future__ import annotations

from ...model import ModelContext, RoomVariables
from ...preparation import normalize_room_type
from ..base import ConstraintSettings
from ..geometry import priority_selection_literals


class FrontAnchorConstraint:
    key = "front_anchor"

    def apply(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> None:
        priority = tuple(
            normalize_room_type(value)
            for value in tuple(
                settings.get("anchor_room_types", ("veranda", "living_room"))
            )
        )
        ordered_candidates: list[RoomVariables] = []
        all_rooms = tuple(context.room_variables.values())
        for room_type in priority:
            ordered_candidates.extend(
                room
                for room in all_rooms
                if room.room.room_type_key == room_type
            )

        for anchor, selected in priority_selection_literals(
            context, ordered_candidates, "front_anchor_selected"
        ):
            anchor_center_y2 = 2 * anchor.y + anchor.length
            for other in all_rooms:
                if other.room.id_key == anchor.room.id_key:
                    continue
                other_center_y2 = 2 * other.y + other.length
                context.model.Add(
                    anchor_center_y2 <= other_center_y2
                ).OnlyEnforceIf([selected, other.present])
