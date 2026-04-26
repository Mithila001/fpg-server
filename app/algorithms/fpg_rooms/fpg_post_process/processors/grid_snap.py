from __future__ import annotations

from app.algorithms.types import RoomBoundaryPayload


def _snap_to_grid(value: float, grid_size: float) -> float:
    if grid_size <= 0:
        return value
    return round(value / grid_size) * grid_size


def snap_solution_rooms_to_grid(
    rooms: list[RoomBoundaryPayload],
    grid_size: float = 8.0,
) -> list[RoomBoundaryPayload]:
    """Snap normalized room boundaries to a uniform square grid."""
    snapped_rooms: list[RoomBoundaryPayload] = []

    for room in rooms:
        x = float(room["x"])
        y = float(room["y"])
        x_end = float(room["x_end"])
        y_end = float(room["y_end"])

        sx = _snap_to_grid(x, grid_size)
        sy = _snap_to_grid(y, grid_size)
        sx_end = _snap_to_grid(x_end, grid_size)
        sy_end = _snap_to_grid(y_end, grid_size)

        # Preserve positive dimensions after snapping.
        if sx_end <= sx:
            sx_end = sx + grid_size
        if sy_end <= sy:
            sy_end = sy + grid_size

        snapped_rooms.append(
            {
                "name": room["name"],
                "type": room["type"],
                "x": sx,
                "y": sy,
                "x_end": sx_end,
                "y_end": sy_end,
            }
        )

    return snapped_rooms
