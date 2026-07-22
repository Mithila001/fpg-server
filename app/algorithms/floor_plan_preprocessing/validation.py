from __future__ import annotations

import math

from app.algorithms.types_new import FloorPlanGenerationSpec, RoomType

from .config import ExcessAttachedBathroomPolicy, PreprocessingPolicy
from .context import NormalizedRequest, PreparedReferenceData, PreprocessingContext
from .contracts import (
    FloorLimits,
    PreprocessingInput,
    PreprocessingReferenceData,
    PreprocessingRequest,
    RequestedRoom,
    RoomRelationReference,
    RoomSizeReference,
)
from .exceptions import (
    ContextValidationError,
    InputValidationError,
    OutputValidationError,
    ReferenceDataError,
)


def _finite_number(value: object, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise InputValidationError(f"{field} must be numeric")
    if not isinstance(value, (int, float, str)):
        raise InputValidationError(f"{field} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{field} must be numeric") from exc
    if not math.isfinite(number) or (positive and number <= 0):
        suffix = " and greater than zero" if positive else ""
        raise InputValidationError(f"{field} must be finite{suffix}")
    return number


def _validate_attached_bathroom_count(
    request: PreprocessingRequest,
    policy: PreprocessingPolicy,
) -> None:
    if (
        policy.excess_attached_bathrooms
        is not ExcessAttachedBathroomPolicy.REJECT
    ):
        return

    bedroom_count = sum(
        room.room_type is RoomType.BEDROOM for room in request.rooms
    )
    attached_bathroom_count = sum(
        room.room_type is RoomType.ATTACHED_BATHROOM
        for room in request.rooms
    )

    if attached_bathroom_count > bedroom_count:
        raise InputValidationError(
            f"Requested {attached_bathroom_count} attached bathroom(s), "
            f"but only {bedroom_count} bedroom(s) were provided. "
            "Each attached bathroom requires a unique bedroom."
        )


def validate_input(value: PreprocessingInput) -> None:
    if not isinstance(value, PreprocessingInput):
        raise InputValidationError("input must be a PreprocessingInput")
    request = value.request
    if not isinstance(request, PreprocessingRequest):
        raise InputValidationError("request must be a PreprocessingRequest")
    if not isinstance(request.floor_limits, FloorLimits):
        raise InputValidationError("floor_limits must be a FloorLimits")
    _finite_number(request.floor_limits.max_width, "max_width", positive=True)
    _finite_number(request.floor_limits.max_length, "max_length", positive=True)
    if not request.rooms:
        raise InputValidationError("At least one requested room is required")
    for index, room in enumerate(request.rooms):
        if not isinstance(room, RequestedRoom):
            raise InputValidationError(
                f"rooms[{index}] must be a RequestedRoom"
            )
        if not isinstance(room.required, bool):
            raise InputValidationError(f"rooms[{index}].required must be a boolean")
        if room.id is not None and not isinstance(room.id, str):
            raise InputValidationError(f"rooms[{index}].id must be a string or None")
    if not isinstance(value.reference_data, PreprocessingReferenceData):
        raise InputValidationError(
            "reference_data must be PreprocessingReferenceData"
        )
    for index, item in enumerate(value.reference_data.room_sizes):
        if not isinstance(item, RoomSizeReference):
            raise InputValidationError(
                f"room_sizes[{index}] must be a RoomSizeReference"
            )
    for index, item in enumerate(value.reference_data.room_relations):
        if not isinstance(item, RoomRelationReference):
            raise InputValidationError(
                f"room_relations[{index}] must be a RoomRelationReference"
            )
        if not isinstance(item.required, bool):
            raise InputValidationError(
                f"room_relations[{index}].required must be a boolean"
            )
    validate_policy(value.policy)
    _validate_attached_bathroom_count(request, value.policy)


def validate_policy(policy: PreprocessingPolicy) -> None:
    if not isinstance(policy, PreprocessingPolicy):
        raise InputValidationError("policy must be a PreprocessingPolicy")
    minimum = _finite_number(policy.min_aspect_ratio, "min_aspect_ratio", positive=True)
    maximum = _finite_number(policy.max_aspect_ratio, "max_aspect_ratio", positive=True)
    if minimum > maximum:
        raise InputValidationError("min_aspect_ratio cannot exceed max_aspect_ratio")
    _finite_number(policy.floor_area_buffer, "floor_area_buffer")
    if policy.floor_area_buffer < 0:
        raise InputValidationError("floor_area_buffer cannot be negative")
    if (
        isinstance(policy.hallway_count, bool)
        or not isinstance(policy.hallway_count, int)
        or policy.hallway_count < 0
    ):
        raise InputValidationError("hallway_count must be a non-negative integer")
    _finite_number(policy.hallway_min_width, "hallway_min_width", positive=True)
    _finite_number(policy.hallway_min_length, "hallway_min_length", positive=True)
    if not isinstance(policy.default_room_size, str) or not policy.default_room_size.strip():
        raise InputValidationError("default_room_size cannot be empty")


def validate_normalized_request(
    request: NormalizedRequest, policy: PreprocessingPolicy
) -> None:
    if not policy.min_aspect_ratio <= request.aspect_ratio <= policy.max_aspect_ratio:
        raise InputValidationError(
            "aspect_ratio must be between "
            f"{policy.min_aspect_ratio} and {policy.max_aspect_ratio} inclusive"
        )
    ids = [room.id for room in request.rooms]
    duplicates = sorted({room_id for room_id in ids if ids.count(room_id) > 1})
    if duplicates:
        raise InputValidationError("Duplicate room ID(s): " + ", ".join(duplicates))
    if any(not room.id.strip() for room in request.rooms):
        raise InputValidationError("Room IDs cannot be empty")


def validate_reference_data(reference_data: PreparedReferenceData) -> None:
    seen: set[tuple[RoomType, str]] = set()
    for index, item in enumerate(reference_data.room_sizes):
        key = (item.room_type, item.size)
        if not item.size:
            raise ReferenceDataError(f"room_sizes[{index}].size cannot be empty")
        if key in seen:
            raise ReferenceDataError(
                f"Duplicate room-size reference for {key[0].value}/{key[1]}"
            )
        seen.add(key)
        values = (
            item.min_width,
            item.max_width,
            item.min_length,
            item.max_length,
            item.min_area,
            item.max_area,
        )
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ReferenceDataError(
                f"Room-size reference {key[0].value}/{key[1]} must be positive and finite"
            )
        if item.min_width > item.max_width or item.min_length > item.max_length:
            raise ReferenceDataError(
                f"Invalid dimension range for {key[0].value}/{key[1]}"
            )
        if item.min_area > item.max_area:
            raise ReferenceDataError(
                f"Invalid area range for {key[0].value}/{key[1]}"
            )
        if item.min_area > item.max_width * item.max_length:
            raise ReferenceDataError(
                f"Minimum area cannot fit dimension bounds for {key[0].value}/{key[1]}"
            )
        if item.max_area < item.min_width * item.min_length:
            raise ReferenceDataError(
                f"Maximum area is below minimum dimensions for {key[0].value}/{key[1]}"
            )
    for index, relation in enumerate(reference_data.room_relations):
        if not relation.target_room_types:
            raise ReferenceDataError(
                f"room_relations[{index}] must contain at least one target type"
            )
        if len(set(relation.target_room_types)) != len(relation.target_room_types):
            raise ReferenceDataError(
                f"room_relations[{index}] contains duplicate target types"
            )


def validate_context(context: PreprocessingContext) -> None:
    if not context.rooms:
        raise ContextValidationError("Prepared context contains no rooms")
    if context.minimum_required_area > context.floor.width * context.floor.length:
        raise ContextValidationError("Selected floor does not meet minimum required area")


def validate_output(
    specification: FloorPlanGenerationSpec, policy: PreprocessingPolicy
) -> None:
    if specification.floor.width <= 0 or specification.floor.length <= 0:
        raise OutputValidationError("Final floor dimensions must be positive")
    if not specification.rooms:
        raise OutputValidationError("Final specification must contain rooms")
    ids = [str(room.id) for room in specification.rooms]
    if len(ids) != len(set(ids)):
        raise OutputValidationError("Final room IDs must be unique")
    room_types = [room.room_type for room in specification.rooms]
    required_types = set(policy.mandatory_room_types)
    if policy.derive_living_room:
        required_types.add(RoomType.LIVING_ROOM)
    missing = required_types.difference(room_types)
    if missing:
        raise OutputValidationError(
            "Final specification is missing required room types: "
            + ", ".join(sorted(item.value for item in missing))
        )
    for room_type in required_types:
        if not any(
            room.room_type is room_type and room.required
            for room in specification.rooms
        ):
            raise OutputValidationError(
                f"Required room type '{room_type.value}' is not marked required"
            )
    if room_types.count(RoomType.HALLWAY) < policy.hallway_count:
        raise OutputValidationError("Final specification has too few hallways")
    known_ids = set(ids)
    for room in specification.rooms:
        size = room.size
        if (
            size.min_width <= 0
            or size.min_length <= 0
            or size.min_width > size.max_width
            or size.min_length > size.max_length
            or size.min_area <= 0
            or size.min_area > size.max_area
        ):
            raise OutputValidationError(f"Invalid size specification for '{room.id}'")
    for relation in specification.room_relations:
        if str(relation.source_room_id) not in known_ids:
            raise OutputValidationError("Relation has an unknown source room")
        if not relation.target_room_ids or any(
            str(target) not in known_ids for target in relation.target_room_ids
        ):
            raise OutputValidationError("Relation has an unknown or empty target")
