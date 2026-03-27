from __future__ import annotations

from typing import Any
from ortools.sat.python import cp_model

from .constraints import add_internal_doors_placement_constraint, add_main_door_to_outside_constraint
from .solver_models import from_scaled_int, to_scaled_int
from .types.opening import OpeningRunResult
from .utils import get_exterior_sides, get_internal_door_candidates, is_room_type, normalize_rooms


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
			self._warnings = ["No livingRoom found; no mainDoor generated"]

		openings: list[dict[str, Any]] = []
		warnings: list[str] = list(self._warnings)

		for living_room in living_rooms:
			exterior_sides = get_exterior_sides(
				target_room=living_room,
				all_rooms=normalized_rooms,
				tolerance=self.tolerance,
			)

			if not exterior_sides:
				warnings.append(
					f"No valid exterior wall for livingRoom '{living_room['name']}'"
				)
				continue

			model = cp_model.CpModel()
			scaled_room = {
				"x": to_scaled_int(living_room["x"]),
				"y": to_scaled_int(living_room["y"]),
				"x_end": to_scaled_int(living_room["x_end"]),
				"y_end": to_scaled_int(living_room["y_end"]),
			}

			preferred_len_int = to_scaled_int(self.preferred_door_length)
			decision_vars, priority_cost = add_main_door_to_outside_constraint(
				model=model,
				room=scaled_room,
				exterior_sides=exterior_sides,
				side_priority=self.side_priority,
				preferred_door_length=preferred_len_int,
			)
			model.Minimize(priority_cost)

			solver = cp_model.CpSolver()
			solver.parameters.max_time_in_seconds = 1.0
			solver.parameters.num_search_workers = 1
			status = solver.Solve(model)

			if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
				warnings.append(
					f"No valid CP-SAT opening for livingRoom '{living_room['name']}'"
				)
				continue

			selected_side = None
			for side, bool_var in decision_vars["side_selected"].items():
				if solver.Value(bool_var) == 1:
					selected_side = side
					break

			if selected_side is None:
				warnings.append(
					f"CP-SAT did not pick a side for livingRoom '{living_room['name']}'"
				)
				continue

			openings.append(
				{
					"room_name": living_room["name"],
					"room_type": living_room["type"],
					"opening_type": "mainDoor",
					"side": selected_side,  # type: ignore[typeddict-item]
					"x1": from_scaled_int(solver.Value(decision_vars["x1"])),
					"y1": from_scaled_int(solver.Value(decision_vars["y1"])),
					"x2": from_scaled_int(solver.Value(decision_vars["x2"])),
					"y2": from_scaled_int(solver.Value(decision_vars["y2"])),
				}
			)

		internal_candidates = get_internal_door_candidates(
			all_rooms=normalized_rooms,
			preferred_door_length=self.preferred_door_length,
			tolerance=self.tolerance,
		)
		if internal_candidates:
			internal_model = cp_model.CpModel()
			internal_decisions = add_internal_doors_placement_constraint(
				model=internal_model,
				candidates=internal_candidates,
			)

			internal_solver = cp_model.CpSolver()
			internal_solver.parameters.max_time_in_seconds = 1.0
			internal_solver.parameters.num_search_workers = 1
			internal_status = internal_solver.Solve(internal_model)

			if internal_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
				for index, selected_var in enumerate(internal_decisions["selected"]):
					if internal_solver.Value(selected_var) != 1:
						continue
					candidate = internal_candidates[index]
					openings.append(
						{
							"room_name": candidate["room_a_name"],
							"room_type": candidate["room_a_type"],
							"opening_type": "internalDoor",
							"side": candidate["side"],  # type: ignore[typeddict-item]
							"x1": candidate["x1"],
							"y1": candidate["y1"],
							"x2": candidate["x2"],
							"y2": candidate["y2"],
							"connected_room_name": candidate["room_b_name"],
							"connected_room_type": candidate["room_b_type"],
						}
					)
			else:
				warnings.append("Internal door constraint solve failed")

		self._openings = openings
		self._warnings = warnings

		if openings:
			self.last_status_name = "SUCCESS"
		elif warnings:
			if not living_rooms:
				self.last_status_name = "NO_LIVING_ROOM"
			else:
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
