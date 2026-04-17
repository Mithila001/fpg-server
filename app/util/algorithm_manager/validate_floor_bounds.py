from app.algorithms.fpg_rooms.types.room import FpgRequirements
from app.core.fpg_rooms.config_fpg import (
    HALLWAY_GENERATOR_MIN_HEIGHT,
    HALLWAY_GENERATOR_MIN_WIDTH,
    LIVING_ROOM_MIN_HEIGHT,
    LIVING_ROOM_MIN_WIDTH,
    MIN_FLOOR_AREA_BUFFER,
    MIN_FLOOR_HEIGHT,
    MIN_FLOOR_WIDTH,
)


def validate_and_compute_floor_bounds(
    floor_width: int,
    floor_height: int,
    requirements: FpgRequirements,
) -> dict[str, object]:
    """Validate floor dimensions against minimum required area constraints."""
    print("\n _validate_and_compute_floor_bounds()")

    if floor_width < MIN_FLOOR_WIDTH or floor_height < MIN_FLOOR_HEIGHT:
        raise Exception(
            f"Floor dimensions are too small. "
            f"Received: {floor_width} x {floor_height}, "
            f"Minimum required: {MIN_FLOOR_WIDTH} x {MIN_FLOOR_HEIGHT}"
        )

    total_min_area = 0.0
    for room in requirements.rooms:
        min_w = getattr(room, "min_w", None)
        min_h = getattr(room, "min_h", None)

        if min_w is None or min_h is None:
            raise Exception(
                f"Room '{getattr(room, 'name', '<unknown>')}' has missing min dimensions"
            )

        try:
            total_min_area += float(min_w) * float(min_h)
        except (TypeError, ValueError):
            raise Exception(
                f"Room '{getattr(room, 'name', '<unknown>')}' has invalid dimensions"
            )

    # API validation uses one hallway minimum area as a baseline requirement.
    total_min_area += float(LIVING_ROOM_MIN_WIDTH) * float(LIVING_ROOM_MIN_HEIGHT)
    total_min_area += float(HALLWAY_GENERATOR_MIN_WIDTH) * float(HALLWAY_GENERATOR_MIN_HEIGHT)

    total_min_area_with_buffer = total_min_area + MIN_FLOOR_AREA_BUFFER
    floor_area = float(floor_width) * float(floor_height)

    if total_min_area_with_buffer > floor_area:
        shortage = total_min_area_with_buffer - floor_area
        raise Exception(
            f"Insufficient floor area. Total minimum room area + buffer = "
            f"{total_min_area:.2f} + {MIN_FLOOR_AREA_BUFFER} = {total_min_area_with_buffer:.2f}, "
            f"but floor area = {floor_width} × {floor_height} = {floor_area:.2f}. "
            f"Shortage: {shortage:.2f} square units."
        )

    return {
        "status": "OK",
        "message": "Floor dimensions validated successfully",
    }
