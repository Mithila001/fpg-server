from __future__ import annotations

from collections.abc import Mapping

from ...exceptions import InvalidProfileError
from ...model import ModelContext, RoomVariables
from ...preparation import normalize_room_type
from ..base import ConstraintSettings
from ..geometry import priority_selection_literals


class RoomSizeHierarchyConstraint:
    """Constrain selected room-type areas relative to an anchor room area."""

    key = "room_size_hierarchy"

    def apply(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> None:
        raw_rules = settings.get("ratios_by_room_type", {})
        if not isinstance(raw_rules, Mapping) or not raw_rules:
            return

        precision = int(settings.get("precision", 1000))
        if precision < 1:
            raise InvalidProfileError("room_size_hierarchy.precision must be positive")

        priority = tuple(
            normalize_room_type(value)
            for value in tuple(
                settings.get("anchor_room_types", ("living_room",))
            )
        )
        all_rooms = tuple(context.room_variables.values())
        candidates: list[RoomVariables] = []
        for room_type in priority:
            candidates.extend(
                room
                for room in all_rooms
                if room.room.room_type_key == room_type
            )

        selected_anchors = priority_selection_literals(
            context, candidates, "size_anchor_selected"
        )
        for variables in all_rooms:
            raw_rule = raw_rules.get(variables.room.room_type_key)
            if not isinstance(raw_rule, Mapping):
                continue
            min_ratio = float(raw_rule.get("min_ratio", 0.0))
            max_ratio = float(raw_rule.get("max_ratio", 1.0))
            if min_ratio < 0 or max_ratio < min_ratio:
                raise InvalidProfileError(
                    f"Invalid size hierarchy for '{variables.room.room_type_key}'"
                )
            min_scaled = int(round(min_ratio * precision))
            max_scaled = int(round(max_ratio * precision))

            for anchor, selected in selected_anchors:
                if anchor.room.id_key == variables.room.id_key:
                    continue
                context.model.Add(
                    variables.area * precision >= anchor.area * min_scaled
                ).OnlyEnforceIf([selected, variables.present])
                context.model.Add(
                    variables.area * precision <= anchor.area * max_scaled
                ).OnlyEnforceIf([selected, variables.present])
