from __future__ import annotations

from typing import Any, Sequence

from app.core.fpg_rooms.config_fpg import NOT_PRUNE_ROOMS
from app.schemas.db.room_setup_template import RoomSetupTemplateBase


def _as_clean_str(value: Any) -> str:
    return str(value or "").strip()


def _extract_template_room_types(room_template: RoomSetupTemplateBase) -> set[str]:
    if room_template is None:
        raise ValueError("Room template is required.")

    template_data = getattr(room_template, "data", None)
    if not isinstance(template_data, list):
        raise ValueError("Room template data must be a list.")

    room_types: set[str] = set()
    for index, entry in enumerate(template_data):
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid room template entry at index {index}: expected object.")

        room_type = _as_clean_str(entry.get("type"))
        if not room_type:
            raise ValueError(f"Missing room type in template entry at index {index}.")

        room_types.add(room_type)

    return room_types


def _get_constraint_room_type(constraint: Any) -> str:
    if isinstance(constraint, dict):
        return _as_clean_str(constraint.get("type") or constraint.get("room_type"))

    return _as_clean_str(getattr(constraint, "type", None) or getattr(constraint, "room_type", None))


def _get_related_room_values(constraint: Any) -> Any:
    if isinstance(constraint, dict):
        return constraint.get("related_room")

    return getattr(constraint, "related_room", None)


def _set_related_room_values(constraint: Any, related_room: list[str]) -> None:
    if isinstance(constraint, dict):
        constraint["related_room"] = related_room
        return

    if hasattr(constraint, "related_room"):
        setattr(constraint, "related_room", related_room)


def prune_room_relations_constraints_by_template(
    room_template: RoomSetupTemplateBase,
    room_relations_constraints: Sequence[Any],
) -> tuple[list[Any], str | None]:
    """Keep only relation rules relevant to room types present in template.

    Removes any rule whose `room_type` is absent from the template,
    and trims each rule's `related_room` list to include only template types.
    """
    try:
        template_room_types = _extract_template_room_types(room_template)

        if not isinstance(room_relations_constraints, Sequence):
            return [], "Room relations constraints must be a sequence."

        filtered_constraints: list[Any] = []
        for index, constraint in enumerate(room_relations_constraints):
            room_type = _get_constraint_room_type(constraint)
            if not room_type:
                return [], f"Missing room_type in room relations constraint at index {index}."

            if room_type in NOT_PRUNE_ROOMS:
                filtered_constraints.append(constraint)
                continue

            if room_type not in template_room_types:
                continue

            related_room_raw = _get_related_room_values(constraint)
            if related_room_raw is not None:
                if not isinstance(related_room_raw, list):
                    return [], (
                        "Invalid related_room in room relations constraint "
                        f"at index {index}: expected list."
                    )

                allowed_related_room_types = template_room_types.union(NOT_PRUNE_ROOMS)
                sanitized_related_room = [
                    related_type
                    for related_type in (_as_clean_str(value) for value in related_room_raw)
                    if related_type and related_type in allowed_related_room_types
                ]
                _set_related_room_values(constraint, sanitized_related_room)

            filtered_constraints.append(constraint)

        return filtered_constraints, None
    except Exception as exc:
        return [], f"Relation constraint pruning failed: {exc}"

# Keep alias for backward compatibility in case any other module used old name
prune_room_size_constraints_by_template = prune_room_relations_constraints_by_template
