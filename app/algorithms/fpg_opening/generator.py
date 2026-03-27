from __future__ import annotations

from typing import Any

from .constraints import select_main_door
from .types.opening import OpeningRunResult
from .utils import get_exterior_sides, is_room_type, normalize_rooms


class OpeningGenerator:
	"""Generate opening payloads from room-layout rectangles.

	This module is intentionally isolated from fpg_rooms internals and only
	depends on the room-result payload schema.
	"""

	def __init__(
		self,
		fpg_room_requirements: list[dict[str, Any]],
		side_priority: tuple[str, ...] = ("south", "east", "north", "west"),
		preferred_door_length: float = 8.0,
		tolerance: float = 1e-6,
	) -> None:
		self.fpg_room_requirements = fpg_room_requirements
		self.side_priority = side_priority
		self.preferred_door_length = float(preferred_door_length)
		self.tolerance = float(tolerance)

		self.last_status_name: str = "NOT_RUN"
		self._warnings: list[str] = []
		self._openings: list[dict[str, Any]] = []

	def generate(self) -> bool:
		"""Compute one mainDoor opening for each livingRoom where possible."""
		if not isinstance(self.fpg_room_requirements, list):
			self.last_status_name = "INVALID_INPUT"
			self._warnings = ["fpg_room_requirements must be a list"]
			self._openings = []
			return False

		try:
			normalized_rooms = normalize_rooms(self.fpg_room_requirements)
		except ValueError as exc:
			self.last_status_name = "INVALID_INPUT"
			self._warnings = [str(exc)]
			self._openings = []
			return False

		living_rooms = [room for room in normalized_rooms if is_room_type(room, "livingRoom")]
		if not living_rooms:
			self.last_status_name = "NO_LIVING_ROOM"
			self._warnings = ["No livingRoom found; no mainDoor generated"]
			self._openings = []
			return True

		openings: list[dict[str, Any]] = []
		warnings: list[str] = []

		for living_room in living_rooms:
			exterior_sides = get_exterior_sides(
				target_room=living_room,
				all_rooms=normalized_rooms,
				tolerance=self.tolerance,
			)

			main_door = select_main_door(
				room=living_room,
				exterior_sides=exterior_sides,
				side_priority=self.side_priority,
				preferred_door_length=self.preferred_door_length,
			)

			if main_door is None:
				warnings.append(
					f"No valid exterior wall for livingRoom '{living_room['name']}'"
				)
				continue

			openings.append(main_door)

		self._openings = openings
		self._warnings = warnings

		if openings:
			self.last_status_name = "SUCCESS"
		elif warnings:
			self.last_status_name = "NO_VALID_OPENING"
		else:
			self.last_status_name = "EMPTY_RESULT"

		return True

	def get_solution(self) -> OpeningRunResult:
		message = {
			"SUCCESS": "Openings generated",
			"NO_LIVING_ROOM": "No livingRoom found",
			"NO_VALID_OPENING": "No valid opening generated for livingRoom",
			"INVALID_INPUT": "Invalid input for opening generator",
			"EMPTY_RESULT": "No openings generated",
			"NOT_RUN": "Generator has not run",
		}.get(self.last_status_name, "Unknown opening solver status")

		return {
			"status": self.last_status_name,
			"message": message,
			"openings": self._openings,
			"warnings": self._warnings,
		}


def generate_main_doors(
	fpg_room_requirements: list[dict[str, Any]],
	side_priority: tuple[str, ...] = ("south", "east", "north", "west"),
	preferred_door_length: float = 8.0,
	tolerance: float = 1e-6,
) -> OpeningRunResult:
	"""Convenience wrapper used by pipeline orchestration code."""
	generator = OpeningGenerator(
		fpg_room_requirements=fpg_room_requirements,
		side_priority=side_priority,
		preferred_door_length=preferred_door_length,
		tolerance=tolerance,
	)
	generator.generate()
	return generator.get_solution()
