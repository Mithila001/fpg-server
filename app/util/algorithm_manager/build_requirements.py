import math
from collections import Counter
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


def _sanitize_attached_bathrooms(room_template_data: List[dict]) -> List[dict]:
    bedroom_count = sum(1 for r in room_template_data if str(r.get("type", "")).strip().lower() == "bedroom")
    
    sanitized_data = []
    attached_bathroom_count = 0
    for r in room_template_data:
        if str(r.get("type", "")).strip().lower() == "attachedbathroom":
            if attached_bathroom_count >= bedroom_count:
                continue
            attached_bathroom_count += 1
        sanitized_data.append(r)
    return sanitized_data


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


def _select_majority_room_size(
    room_template_data: List[dict],
    default_size: str = "regular",
    excluded_types: set[str] | None = None,
) -> str:
    if not room_template_data:
        return default_size

    excluded = {t.lower() for t in (excluded_types or set())}
    size_counter: Counter[str] = Counter()
    for room in room_template_data:
        if not isinstance(room, dict):
            continue
        room_type = str(room.get("type") or "").strip().lower()
        if not room_type or room_type in excluded:
            continue
        room_size = str(room.get("size") or "").strip().lower()
        if not room_size:
            continue
        size_counter[room_size] += 1

    if not size_counter:
        return default_size

    max_count = max(size_counter.values())
    tied_sizes = sorted(
        [size for size, count in size_counter.items() if count == max_count]
    )
    if default_size in tied_sizes:
        return default_size
    return tied_sizes[0]


def _normalize_template_sizes(
    room_template_data: List[dict],
    room_size_category: str,
    excluded_types: set[str] | None = None,
) -> List[dict]:
    excluded = {t.lower() for t in (excluded_types or set())}
    normalized_data: List[dict] = []
    for room in room_template_data:
        if not isinstance(room, dict):
            continue
        room_type = str(room.get("type") or "").strip().lower()
        if room_type and room_type not in excluded:
            normalized_room = dict(room)
            normalized_room["size"] = room_size_category
            normalized_data.append(normalized_room)
        else:
            normalized_data.append(dict(room))
    return normalized_data


def _validate_majority_size_support(
    room_template_data: List[dict],
    size_constraints: List[RoomSizeConstraint],
    room_size_category: str,
    excluded_types: set[str] | None = None,
) -> None:
    excluded = {t.lower() for t in (excluded_types or set())}
    available_sizes_by_type: dict[str, set[str]] = {}
    for constraint in size_constraints:
        room_type = str(constraint.type or "").strip().lower()
        size_label = str(constraint.size or "").strip().lower()
        if not room_type or not size_label:
            continue
        available_sizes_by_type.setdefault(room_type, set()).add(size_label)

    missing: List[str] = []
    for room in room_template_data:
        if not isinstance(room, dict):
            continue
        room_type = str(room.get("type") or "").strip().lower()
        if not room_type or room_type in excluded:
            continue
        available_sizes = available_sizes_by_type.get(room_type)
        if not available_sizes or room_size_category not in available_sizes:
            missing.append(room_type)

    if missing:
        missing_unique = ", ".join(sorted(set(missing)))
        raise ValueError(
            "Majority size selection is not supported for room type(s): "
            f"{missing_unique}. Missing size '{room_size_category}'."
        )


def build_requirements(
    floor_width: float,
    floor_height: float,
    aspect_ratio: float,
    room_template: RoomSetupTemplateBase,
) -> FpgRequirements:
    """Build FpgRequirements from template, loading and pruning server-side constraints.

    This function now handles all data loading and constraint pruning internally.
    Raises exceptions if any step fails (no silent defaults).
    """
    # print parameter values for debugging
    print(
        f"\n\nBuilding requirements with floor_width: {floor_width}, floor_height: {floor_height}, aspect_ratio: {aspect_ratio}, room_template: {room_template}"
    )

    def _parse_and_validate_aspect_ratio(value) -> float:
        """Parse common aspect-ratio inputs and validate.

        - Accepts numeric values (int/float) representing H/W.
        - Accepts string forms like "2:1" or "1:2" which are interpreted as H:W.
        Returns a float H/W and raises ValueError for invalid inputs or out-of-range values.
        """

        # Accept numeric values directly
        if isinstance(value, (int, float)):
            ratio = float(value)
        elif isinstance(value, str):
            parts = value.split(":")
            if len(parts) != 2:
                raise ValueError(
                    "Invalid aspect_ratio string format. Expect 'H:W' like '2:1' or '1:2'."
                )
            try:
                h = float(parts[0])
                w = float(parts[1])
            except Exception:
                raise ValueError(
                    "Invalid numbers in aspect_ratio string. Expect 'H:W' with numeric parts."
                )
            if w == 0:
                raise ValueError("Invalid aspect_ratio: width part cannot be zero.")
            ratio = h / w
        else:
            raise ValueError(
                "aspect_ratio must be a number or a string of the form 'H:W' (e.g. '2:1')."
            )

        # Allowed inclusive range: H/W in [0.5, 2.0] (covers 1:2 up to 2:1)
        if not (0.5 <= ratio <= 2.0):
            raise ValueError(
                "aspect_ratio must be between 0.5 and 2.0 (inclusive) representing H/W (height/width)."
            )
        return ratio

    # Defensive normalization: accept strings or numbers passed here and ensure range
    aspect_ratio = _parse_and_validate_aspect_ratio(aspect_ratio)

    room_template.data = _sanitize_attached_bathrooms(room_template.data)

    _validate_mandatory_room_types(room_template)

    try:
        _, size_constraints, relation_constraints = load_server_side_data()
        print(f"\nSize Constraints: {size_constraints}")
    except Exception as exc:
        raise Exception(f"Failed to load server-side constraints: {exc}") from exc

    room_size_category = _select_majority_room_size(
        room_template.data,
        default_size="regular",
        excluded_types={"hallway"},
    )
    _validate_majority_size_support(
        room_template.data,
        size_constraints,
        room_size_category,
        excluded_types={"hallway"},
    )
    normalized_template_data = _normalize_template_sizes(
        room_template.data,
        room_size_category,
        excluded_types={"hallway"},
    )
    normalized_template = RoomSetupTemplateBase(
        name=room_template.name,
        data=normalized_template_data,
    )

    floor_width, floor_height = _calculate_suitable_floor_dimensions(
        floor_width=floor_width,
        floor_height=floor_height,
        room_template_data=normalized_template.data,
        size_constraints=size_constraints,
        aspect_ratio=aspect_ratio,
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
    rooms = build_rooms_from_template(normalized_template)
    normalized_rooms = normalize_db_data_requirements(
        rooms,
        size_constraints,
        preferred_living_room_size=room_size_category,
    )

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

    print(f"\n\n Normalized Rooms: {normalized_rooms}\n")

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
    aspect_ratio: float,
    buffer: float,
) -> Tuple[float, float]:
    """
    Calculates the largest rectangle for the provided aspect ratio that fits
    within the original floor dimensions and falls within the min/max area range.
    """

    if not room_template_data:
        raise ValueError("Room template data is empty or missing.")

    # 1. Calculate area boundaries
    total_min_area = 0.0
    total_max_area = 0.0
    constraints_by_type_size: dict[tuple[str, str], RoomSizeConstraint] = {}
    available_sizes_by_type: dict[str, set[str]] = {}
    for constraint in size_constraints:
        room_type = str(constraint.type or "").strip()
        size_label = str(constraint.size or "").strip()
        if not room_type or not size_label:
            continue
        constraints_by_type_size[(room_type, size_label)] = constraint
        if room_type not in available_sizes_by_type:
            available_sizes_by_type[room_type] = set()
        available_sizes_by_type[room_type].add(size_label)

    for room in room_template_data:
        r_type = str(room.get("type") or "").strip()
        r_size = str(room.get("size") or "").strip()

        if not r_size:
            room_id = str(room.get("id") or room.get("name") or "unknown")
            raise ValueError(
                f"Room '{room_id}' of type '{r_type}' is missing required 'size'."
            )

        constraint = constraints_by_type_size.get((r_type, r_size))
        if not constraint:
            available_sizes = sorted(available_sizes_by_type.get(r_type, set()))
            if available_sizes:
                raise ValueError(
                    f"Missing size constraints for room type '{r_type}' with size '{r_size}'. "
                    f"Available sizes: {', '.join(available_sizes)}"
                )
            raise ValueError(f"Missing size constraints for room type: '{r_type}'")

        if constraint.min_area is None or constraint.max_area is None:
            raise ValueError(
                f"Missing area constraints for room type '{r_type}' with size '{r_size}'"
            )

        total_min_area += float(constraint.min_area)
        total_max_area += float(constraint.max_area)

    required_min_total = total_min_area + buffer
    required_max_total = total_max_area + buffer

    # 2. Geometric logic with user-provided ratio: H = W * aspect_ratio
    ratio_factor = aspect_ratio

    # We need to find the maximum Width (W) such that:
    #   1. W <= floor_width
    #   2. W * ratio <= floor_height  =>  W <= floor_height / ratio
    #   3. W * (W * ratio) <= max_area =>  W <= sqrt(max_area / ratio)

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
            f"Constraint Conflict: The largest rectangle for aspect_ratio={ratio_factor:.2f} that fits the building "
            f"({calculated_area:.2f}) is smaller than the required minimum area ({required_min_total:.2f})."
        )

    print("--- Final Aspect-Ratio Floor Dimensions Picked ---")
    print(f"Target Area Range: {required_min_total:.2f} - {required_max_total:.2f}")
    print(f"Aspect Ratio (H/W): {ratio_factor:.2f}")
    print(f"Resulting Width: {best_w:.2f}, Height: {best_h:.2f}")
    print(f"Resulting Area: {calculated_area:.2f}")
    print("-------------------------------------------")

    return best_w, best_h
