from __future__ import annotations

from ...domain import RoomType
from ...model import ModelContext, RoomVariables
from ..base import ConstraintSettings, require_room_types
from ..geometry import priority_selection_literals


class FrontAnchorConstraint:
    key = "front_anchor"

    def apply(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> None:
        priority = require_room_types(
            settings.get(
                "anchor_room_types",
                (RoomType.VERANDA, RoomType.LIVING_ROOM),
            ),
            "front_anchor.anchor_room_types",
        )
        ordered_candidates: list[RoomVariables] = []
        all_rooms = tuple(context.room_variables.values())
        for room_type in priority:
            ordered_candidates.extend(
                room
                for room in all_rooms
                if room.room.room_type is room_type
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
