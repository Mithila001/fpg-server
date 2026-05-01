import math
from typing import Tuple, List
from app.algorithms.types import ConfigData, FpgRequirements
from app.core.fpg_rooms.config_fpg import (
    DEFAULT_ASPECT_RATIO_MAX,
    DEFAULT_ASPECT_RATIO_MIN,
    DEFAULT_HALLWAY_COUNT,
    ENVELOPE_APPLY_SIDES,
    ENVELOPE_ENABLED,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_MAX_GAP,
    ENVELOPE_MIN_GAP,
    MIN_COVERAGE,
    MIN_FLOOR_AREA_BUFFER,
    MANDATORY_ROOMS,
)

# from app.models.room_size_constraint import RoomSizeConstraint
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.types.room_size_constraint import RoomSizeConstraint
from app.util.constraint_pruner import prune_room_relations_constraints_by_template
from app.util.room_requirements import normalize_db_data_requirements
from app.util.algorithm_manager.build_rooms_from_template import (
    build_rooms_from_template,
)
from app.util.algorithm_manager.load_server_side_data import load_server_side_data


def _validate_mandatory_room_types(room_template: RoomSetupTemplateBase) -> None:
    template_data = getattr(room_template, "data", None)
    if not isinstance(template_data, list):
        raise ValueError("Room template data must be a list.")

    present_room_types = {
        str(room.get("type") or "").strip()
        for room in template_data
        if isinstance(room, dict) and str(room.get("type") or "").strip()
    }
    missing_room_types = [
        room_type
        for room_type in MANDATORY_ROOMS
        if room_type not in present_room_types
    ]
    if missing_room_types:
        raise ValueError(
            "Room template is missing mandatory room type(s): "
            + ", ".join(missing_room_types)
        )


def build_requirements(
    floor_width: float,
    floor_height: float,
    room_template: RoomSetupTemplateBase,
) -> FpgRequirements:
    """Build FpgRequirements from template, loading and pruning server-side constraints.

    This function now handles all data loading and constraint pruning internally.
    Raises exceptions if any step fails (no silent defaults).
    """
    # print parameter values for debugging
    print(
        f"\n\nBuilding requirements with floor_width: {floor_width}, floor_height: {floor_height}, room_template: {room_template}"
    )

    _validate_mandatory_room_types(room_template)

    try:
        _, size_constraints, relation_constraints = load_server_side_data(
            should_bypass=True
        )
        print(f"\nSize Constraints: {size_constraints}")
    except Exception as exc:
        raise Exception(f"Failed to load server-side constraints: {exc}") from exc

    floor_width, floor_height = _calculate_suitable_floor_dimensions(
        floor_width=floor_width,
        floor_height=floor_height,
        room_template_data=room_template.data,
        size_constraints=size_constraints,
        buffer=MIN_FLOOR_AREA_BUFFER,
    )

    try:
        relation_constraints, prune_error = (
            prune_room_relations_constraints_by_template(
                room_template=room_template,
                room_relations_constraints=relation_constraints,
            )
        )
        if prune_error:
            raise Exception(f"Failed to prune relation constraints: {prune_error}")
    except Exception as exc:
        raise Exception(f"Failed to prune room relations constraints: {exc}") from exc
    # print(f"\n\n Load Size Constraints : {size_constraints} \n\n")
    rooms = build_rooms_from_template(room_template)
    normalized_rooms = normalize_db_data_requirements(rooms, size_constraints)

    config = ConfigData(
        min_coverage=MIN_COVERAGE,
        max_aspect_ratio=DEFAULT_ASPECT_RATIO_MAX,
        min_aspect_ratio=DEFAULT_ASPECT_RATIO_MIN,
        floor_plan_width=floor_width,
        floor_plan_height=floor_height,
        hallway_count=DEFAULT_HALLWAY_COUNT,
        envelope_enabled=ENVELOPE_ENABLED,
        envelope_min_gap=ENVELOPE_MIN_GAP,
        envelope_max_gap=ENVELOPE_MAX_GAP,
        envelope_exclude_types=ENVELOPE_EXCLUDE_TYPES,
        envelope_apply_sides=ENVELOPE_APPLY_SIDES,
    )

    return FpgRequirements(
        rooms=normalized_rooms,
        config=config,
        relation_constraints=list(relation_constraints),
    )


def _calculate_suitable_floor_dimensions(
    floor_width: float,
    floor_height: float,
    room_template_data: List[dict],
    size_constraints: List[RoomSizeConstraint],  # RoomSizeConstraint
    buffer: float,
) -> Tuple[float, float]:
    """
    Calculates the largest rectangle with a 10:16 aspect ratio that fits
    within the original floor dimensions and falls within the min/max area range.
    """

    if not room_template_data:
        raise ValueError("Room template data is empty or missing.")

    # 1. Calculate area boundaries
    total_min_area = 0.0
    total_max_area = 0.0
    constraint_map = {c.type: c for c in size_constraints}

    for room in room_template_data:
        r_type = str(room.get("type") or "").strip()
        constraint = constraint_map.get(r_type)
        if not constraint:
            raise ValueError(f"Missing size constraints for room type: '{r_type}'")

        total_min_area += constraint.min_area or 0.0
        total_max_area += constraint.max_area or 0.0

    required_min_total = total_min_area + buffer
    required_max_total = total_max_area + buffer

    # 2. Geometric Logic for 10:16 (W:H)
    # Ratio is 10/16 = 0.625. So H = W / 0.625  OR  H = W * 1.6
    ratio_factor = 1.6

    # We need to find the maximum Width (W) such that:
    #   1. W <= floor_width
    #   2. W * 1.6 <= floor_height  =>  W <= floor_height / 1.6
    #   3. W * (W * 1.6) <= max_area =>  W <= sqrt(max_area / 1.6)

    limit_by_width = floor_width
    limit_by_height = floor_height / ratio_factor
    limit_by_max_area = math.sqrt(required_max_total / ratio_factor)

    # The largest width that satisfies ALL constraints
    best_w = min(limit_by_width, limit_by_height, limit_by_max_area)
    best_h = best_w * ratio_factor
    calculated_area = best_w * best_h

    # 3. Validation
    # Check if this "largest possible" rectangle meets the minimum area requirement
    if calculated_area < required_min_total:
        # If the largest possible 10:16 rectangle is still smaller than the minimum area,
        # it means the building is too small or the ratio is too restrictive for these rooms.
        raise ValueError(
            f"Constraint Conflict: The largest 10:16 rectangle that fits the building "
            f"({calculated_area:.2f}) is smaller than the required minimum area ({required_min_total:.2f})."
        )

    print("--- Final 10:16 Floor Dimensions Picked ---")
    print(f"Target Area Range: {required_min_total:.2f} - {required_max_total:.2f}")
    print(f"Resulting Width: {best_w:.2f}, Height: {best_h:.2f}")
    print(f"Resulting Area: {calculated_area:.2f}")
    print("-------------------------------------------")

    return best_w, best_h
