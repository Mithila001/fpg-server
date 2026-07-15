from __future__ import annotations

from ...model import ModelContext
from ...preparation import normalize_room_type
from ..base import ConstraintSettings
from ..geometry import adjacency_literal


class HallwayConnectivityConstraint:
    key = "hallway_connectivity"

    def apply(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> None:
        hallway_types = {
            normalize_room_type(value)
            for value in tuple(settings.get("hallway_room_types", ("hallway",)))
        }
        anchor_types = {
            normalize_room_type(value)
            for value in tuple(
                settings.get("anchor_room_types", ("living_room",))
            )
        }
        minimum_overlap = max(
            1,
            context.problem.scale.minimum_length(
                float(settings.get("minimum_overlap", 0.6))
            ),
        )

        all_rooms = tuple(context.room_variables.values())
        hallways = [
            room for room in all_rooms if room.room.room_type_key in hallway_types
        ]
        anchors = [
            room for room in all_rooms if room.room.room_type_key in anchor_types
        ]
        destinations = [
            room
            for room in all_rooms
            if room.room.room_type_key not in hallway_types | anchor_types
        ]

        for hallway in hallways:
            anchor_options = [
                adjacency_literal(context, hallway, anchor, minimum_overlap)
                for anchor in anchors
                if anchor.room.id_key != hallway.room.id_key
            ]
            destination_options = [
                adjacency_literal(context, hallway, destination, minimum_overlap)
                for destination in destinations
                if destination.room.id_key != hallway.room.id_key
            ]

            if anchor_options:
                context.model.AddBoolOr(
                    anchor_options + [hallway.present.Not()]
                )
            else:
                context.model.Add(hallway.present == 0)

            if destination_options:
                context.model.AddBoolOr(
                    destination_options + [hallway.present.Not()]
                )
            else:
                context.model.Add(hallway.present == 0)
