import math
from typing import List, Sequence

from app.algorithms.types.room import FpgRequirements, RoomData
from app.models.room_size_constraint import RoomSizeConstraint


def floor_values(value: float) -> int:
    """Convert float value to integer by flooring (rounding down).

    Args:
        value: Float value to floor

    Returns:
        Floored integer value (e.g., 5.5 -> 5, 5.3 -> 5, 4.9 -> 4)
    """
    return int(math.floor(value))


def normalize_db_data_requirements(
    rooms: List[RoomData],
    constraints: Sequence[RoomSizeConstraint],
) -> List[RoomData]:
    """Normalize room dimensions from DB constraints with strict validation.

    For each room type, use the DB value when present. If any required dimension
    is missing, raise an error (no defaults allowed).

    Args:
        rooms: List of room instances from template
        constraints: Room size constraints from database

    Returns:
        Normalized rooms with dimensions from constraints

    Raises:
        ValueError: If constraint not found or missing dimensions
    """
    constraints_by_type = {c.type: c for c in constraints}
    normalized: List[RoomData] = []

    for room in rooms:
        if room.type == "livingRoom":
            raise ValueError("ERROR: livingRoom must not be provided by the template")

        constraint = constraints_by_type.get(room.type)

        if not constraint:
            raise ValueError(
                f"ERROR: Room type '{room.type}' has no constraint record in database"
            )

        # Strict validation: all dimensions must be present, no defaults
        if constraint.min_w is None:
            raise ValueError(
                f"ERROR: Room type '{room.type}' missing min_w constraint in database"
            )
        if constraint.min_h is None:
            raise ValueError(
                f"ERROR: Room type '{room.type}' missing min_h constraint in database"
            )
        if constraint.max_w is None:
            raise ValueError(
                f"ERROR: Room type '{room.type}' missing max_w constraint in database"
            )
        if constraint.max_h is None:
            raise ValueError(
                f"ERROR: Room type '{room.type}' missing max_h constraint in database"
            )

        min_w = int(constraint.min_w)
        min_h = int(constraint.min_h)
        max_w = int(constraint.max_w)
        max_h = int(constraint.max_h)

        # Validate dimension ranges
        if min_w <= 0 or min_h <= 0 or max_w <= 0 or max_h <= 0:
            raise ValueError(
                f"ERROR: Room type '{room.type}' has non-positive dimensions: "
                f"min_w={min_w}, min_h={min_h}, max_w={max_w}, max_h={max_h}"
            )

        if min_w > max_w or min_h > max_h:
            raise ValueError(
                f"ERROR: Room type '{room.type}' has invalid dimension ranges: "
                f"min_w={min_w} > max_w={max_w} or min_h={min_h} > max_h={max_h}"
            )

        normalized.append(
            RoomData(
                name=room.name,
                type=room.type,
                min_w=min_w,
                min_h=min_h,
                max_w=max_w,
                max_h=max_h,
            )
        )

    living_room_constraint = constraints_by_type.get("livingRoom")
    if not living_room_constraint:
        raise ValueError("ERROR: livingRoom has no constraint record in database")

    if living_room_constraint.min_w is None:
        raise ValueError("ERROR: livingRoom missing min_w constraint in database")
    if living_room_constraint.min_h is None:
        raise ValueError("ERROR: livingRoom missing min_h constraint in database")
    if living_room_constraint.max_w is None:
        raise ValueError("ERROR: livingRoom missing max_w constraint in database")
    if living_room_constraint.max_h is None:
        raise ValueError("ERROR: livingRoom missing max_h constraint in database")

    living_min_w = int(living_room_constraint.min_w)
    living_min_h = int(living_room_constraint.min_h)
    living_max_w = int(living_room_constraint.max_w)
    living_max_h = int(living_room_constraint.max_h)

    if living_min_w <= 0 or living_min_h <= 0 or living_max_w <= 0 or living_max_h <= 0:
        raise ValueError(
            "ERROR: livingRoom has non-positive dimensions: "
            f"min_w={living_min_w}, min_h={living_min_h}, max_w={living_max_w}, max_h={living_max_h}"
        )

    if living_min_w > living_max_w or living_min_h > living_max_h:
        raise ValueError(
            "ERROR: livingRoom has invalid dimension ranges: "
            f"min_w={living_min_w} > max_w={living_max_w} or min_h={living_min_h} > max_h={living_max_h}"
        )

    normalized.append(
        RoomData(
            name="Living Room",
            type="livingRoom",
            min_w=living_min_w,
            min_h=living_min_h,
            max_w=living_max_w,
            max_h=living_max_h,
        )
    )

    return normalized


def compute_floor_plan_dimension_bounds(
    requirements: "FpgRequirements",
) -> dict[str, object]:
    """Compute floor plan min/max bounds based on room requirements.

    The function performs strict validation. On failure, return an error payload
    it can be mapped to API reply to stop the pipeline.

    Returns dict with keys:
    - status: "OK" or "ERROR"
    - message: optional error message
    - total_min_area, total_max_area, floor_area, normalized_aspect_ratio,
      normalized_floor_area, min_floor_width, min_floor_height,
      max_floor_width, max_floor_height
    """
    import math

    if requirements is None:
        return {
            "status": "ERROR",
            "message": "Requirements object is missing.",
        }

    if not hasattr(requirements, "rooms") or not requirements.rooms:
        return {
            "status": "ERROR",
            "message": "Requirements.rooms is empty or missing.",
        }

    if not hasattr(requirements, "config") or requirements.config is None:
        return {
            "status": "ERROR",
            "message": "Requirements.config is missing.",
        }

    width = getattr(requirements.config, "floor_plan_width", None)
    height = getattr(requirements.config, "floor_plan_height", None)

    if width is None or height is None:
        return {
            "status": "ERROR",
            "message": "Floor plan width/height is missing from config.",
        }

    try:
        floor_width = float(width)
        floor_height = float(height)
    except (TypeError, ValueError):
        return {
            "status": "ERROR",
            "message": "Floor plan width/height must be numeric.",
        }

    if floor_width <= 0 or floor_height <= 0:
        return {
            "status": "ERROR",
            "message": "Floor plan width and height must be positive values.",
        }

    total_min_area = 0.0
    total_max_area = 0.0

    for room in requirements.rooms:
        if room is None:
            return {
                "status": "ERROR",
                "message": "Room entry is missing.",
            }

        min_w = getattr(room, "min_w", None)
        min_h = getattr(room, "min_h", None)
        max_w = getattr(room, "max_w", None)
        max_h = getattr(room, "max_h", None)

        if None in (min_w, min_h, max_w, max_h):
            return {
                "status": "ERROR",
                "message": f"Room '{getattr(room, 'name', '<unknown>')}' has missing dimension(s).",
            }

        try:
            min_w_f = float(min_w)
            min_h_f = float(min_h)
            max_w_f = float(max_w)
            max_h_f = float(max_h)
        except (TypeError, ValueError):
            return {
                "status": "ERROR",
                "message": f"Room '{getattr(room, 'name', '<unknown>')}' has invalid dimension(s).",
            }

        if min_w_f <= 0 or min_h_f <= 0 or max_w_f <= 0 or max_h_f <= 0:
            return {
                "status": "ERROR",
                "message": f"Room '{getattr(room, 'name', '<unknown>')}' dimensions must be positive.",
            }

        if min_w_f > max_w_f or min_h_f > max_h_f:
            return {
                "status": "ERROR",
                "message": (
                    f"Room '{getattr(room, 'name', '<unknown>')}' has min dimension larger than max dimension."
                ),
            }

        min_area = min_w_f * min_h_f
        max_area = max_w_f * max_h_f

        if min_area <= 0 or max_area <= 0:
            return {
                "status": "ERROR",
                "message": f"Room '{getattr(room, 'name', '<unknown>')}' area must be positive.",
            }

        if min_area > max_area:
            return {
                "status": "ERROR",
                "message": f"Room '{getattr(room, 'name', '<unknown>')}' has min area larger than max area.",
            }

        total_min_area += min_area
        total_max_area += max_area

    floor_area = floor_width * floor_height
    minimum_required_area = total_min_area + 2500

    if minimum_required_area > floor_area:
        return {
            "status": "ERROR",
            "message": (
                "Impossible Requirements: total min room area + 2500 exceeds floor area. "
                f"required={minimum_required_area:.2f}, available={floor_area:.2f}."
            ),
        }

    raw_aspect_ratio = floor_width / floor_height
    normalized_aspect_ratio = max(1, math.floor(raw_aspect_ratio))

    target_max_area = total_max_area + 2500
    normalized_floor_area = (
        target_max_area if target_max_area < floor_area else floor_area
    )

    min_floor_area = total_min_area

    min_floor_width = math.sqrt(min_floor_area * normalized_aspect_ratio)
    min_floor_height = min_floor_width / normalized_aspect_ratio

    max_floor_width = math.sqrt(normalized_floor_area * normalized_aspect_ratio)
    max_floor_height = max_floor_width / normalized_aspect_ratio

    return {
        "status": "OK",
        "message": "Computed floor plan dimension bounds successfully.",
        "total_min_area": total_min_area,
        "total_max_area": total_max_area,
        "minimum_required_area": minimum_required_area,
        "floor_area": floor_area,
        "normalized_aspect_ratio": normalized_aspect_ratio,
        "normalized_floor_area": normalized_floor_area,
        "min_floor_area": min_floor_area,
        "min_floor_width": min_floor_width,
        "min_floor_height": min_floor_height,
        "max_floor_width": max_floor_width,
        "max_floor_height": max_floor_height,
    }
