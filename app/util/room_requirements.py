from typing import List, Sequence

from app.algorithms.fpg_rooms.types.room import FpgRequirements, RoomData
from app.models.room_size_constraint import RoomSizeConstraint


def normalize_db_data_requirements(
    rooms: List[RoomData],
    constraints: Sequence[RoomSizeConstraint],
) -> List[RoomData]:
    """Normalize room dimensions from DB constraints with simple defaults.

    For each room type, use the DB value when present; otherwise use 10.
    """
    constraints_by_type = {c.type: c for c in constraints}
    normalized: List[RoomData] = []

    for room in rooms:
        constraint = constraints_by_type.get(room.type)

        if not constraint:
            raise ValueError(
                f"ERROR: Room type '{room.type}' has no constraint record in database"
            )

        min_w = int(constraint.min_w) if constraint.min_w is not None else 10
        min_h = int(constraint.min_h) if constraint.min_h is not None else 10
        max_w = int(constraint.max_w) if constraint.max_w is not None else 100
        max_h = int(constraint.max_h) if constraint.max_h is not None else 100

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

    return normalized


def compute_floor_plan_dimension_bounds(requirements: "FpgRequirements") -> dict[str, object]:
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
    normalized_floor_area = target_max_area if target_max_area < floor_area else floor_area

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
