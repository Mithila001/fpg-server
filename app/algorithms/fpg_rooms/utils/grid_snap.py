from __future__ import annotations

from typing import Any


def _snap_to_grid(value: float, grid_size: float) -> float:
	if grid_size <= 0:
		return value
	return round(value / grid_size) * grid_size


def _normalize_room_bounds(room: dict[str, Any]) -> tuple[float, float, float, float] | None:
	"""Extract room bounds from (x,y,w,h) or (x,y,x_end,y_end) inputs."""
	try:
		x = float(room["x"])
		y = float(room["y"])

		w = room.get("w")
		h = room.get("h")
		x_end = room.get("x_end")
		y_end = room.get("y_end")

		if x_end is None:
			if w is None:
				return None
			x_end = x + float(w)
		else:
			x_end = float(x_end)

		if y_end is None:
			if h is None:
				return None
			y_end = y + float(h)
		else:
			y_end = float(y_end)

		if x_end <= x or y_end <= y:
			return None

		return x, y, x_end, y_end
	except (KeyError, TypeError, ValueError):
		return None


def _snap_room(room: dict[str, Any], index: int, grid_size: float) -> dict[str, Any] | None:
	bounds = _normalize_room_bounds(room)
	if bounds is None:
		return None

	x, y, x_end, y_end = bounds
	sx = _snap_to_grid(x, grid_size)
	sy = _snap_to_grid(y, grid_size)
	sx_end = _snap_to_grid(x_end, grid_size)
	sy_end = _snap_to_grid(y_end, grid_size)

	# Preserve a positive area after snapping.
	if sx_end <= sx:
		sx_end = sx + grid_size
	if sy_end <= sy:
		sy_end = sy + grid_size

	return {
		"name": str(room.get("name") or f"room_{index}"),
		"type": str(room.get("type") or ""),
		"x": sx,
		"y": sy,
		"w": sx_end - sx,
		"h": sy_end - sy,
	}


def snap_solution_rooms_to_grid(
	solution: list[dict[str, Any]],
	grid_size: float = 8.0,
) -> list[dict[str, Any]]:
	"""Return solver rooms snapped to a uniform square grid."""
	snapped_rooms: list[dict[str, Any]] = []

	for idx, room in enumerate(solution):
		snapped = _snap_room(room, idx, grid_size)
		if snapped is not None:
			snapped_rooms.append(snapped)

	return snapped_rooms
