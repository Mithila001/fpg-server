from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ortools.sat.python import cp_model

from .preparation import PreparedProblem, PreparedRoom
from .profiles import GenerationProfile


@dataclass(slots=True)
class RoomVariables:
    room: PreparedRoom
    present: Any
    x: Any
    y: Any
    width: Any
    height: Any
    x_end: Any
    y_end: Any
    area: Any
    x_interval: Any
    y_interval: Any


@dataclass(slots=True)
class ModelContext:
    model: Any
    problem: PreparedProblem
    profile: GenerationProfile
    room_variables: dict[str, RoomVariables]
    adjacency_cache: dict[tuple[str, str, int], Any] = field(default_factory=dict)
    _name_counter: int = 0

    def variables_for(self, room_id_key: str) -> RoomVariables:
        return self.room_variables[room_id_key]

    def new_name(self, prefix: str, *parts: object) -> str:
        self._name_counter += 1
        suffix = "_".join(str(part) for part in parts if str(part))
        if suffix:
            return f"{prefix}_{suffix}_{self._name_counter}"
        return f"{prefix}_{self._name_counter}"


@dataclass(frozen=True, slots=True)
class BuiltModel:
    context: ModelContext
    has_objective: bool
    applied_hard_constraints: tuple[str, ...]
    applied_soft_constraints: tuple[str, ...]
    penalty_terms: tuple[str, ...]


def _create_room_variables(
    model: Any,
    problem: PreparedProblem,
    room: PreparedRoom,
) -> RoomVariables:
    prefix = room.variable_name
    floor = problem.floor

    present = model.NewBoolVar(f"{prefix}_present")
    x = model.NewIntVar(0, floor.width, f"{prefix}_x")
    y = model.NewIntVar(0, floor.height, f"{prefix}_y")
    width = model.NewIntVar(0, room.max_width, f"{prefix}_width")
    height = model.NewIntVar(0, room.max_height, f"{prefix}_height")
    x_end = model.NewIntVar(0, floor.width, f"{prefix}_x_end")
    y_end = model.NewIntVar(0, floor.height, f"{prefix}_y_end")
    area = model.NewIntVar(0, room.max_area, f"{prefix}_area")

    model.Add(x_end == x + width)
    model.Add(y_end == y + height)
    model.AddMultiplicationEquality(area, [width, height])

    model.Add(width >= room.min_width).OnlyEnforceIf(present)
    model.Add(height >= room.min_height).OnlyEnforceIf(present)
    model.Add(area >= room.min_area).OnlyEnforceIf(present)
    model.Add(area <= room.max_area).OnlyEnforceIf(present)

    model.Add(x == 0).OnlyEnforceIf(present.Not())
    model.Add(y == 0).OnlyEnforceIf(present.Not())
    model.Add(width == 0).OnlyEnforceIf(present.Not())
    model.Add(height == 0).OnlyEnforceIf(present.Not())
    model.Add(x_end == 0).OnlyEnforceIf(present.Not())
    model.Add(y_end == 0).OnlyEnforceIf(present.Not())
    model.Add(area == 0).OnlyEnforceIf(present.Not())

    if room.required:
        model.Add(present == 1)

    x_interval = model.NewOptionalIntervalVar(
        x, width, x_end, present, f"{prefix}_x_interval"
    )
    y_interval = model.NewOptionalIntervalVar(
        y, height, y_end, present, f"{prefix}_y_interval"
    )

    return RoomVariables(
        room=room,
        present=present,
        x=x,
        y=y,
        width=width,
        height=height,
        x_end=x_end,
        y_end=y_end,
        area=area,
        x_interval=x_interval,
        y_interval=y_interval,
    )


def create_model_context(
    problem: PreparedProblem,
    profile: GenerationProfile,
) -> ModelContext:
    """Create variables and mandatory model invariants.

    Containment, room size/area ranges, required-room presence, and non-overlap
    are structural invariants. Profiles cannot disable them.
    """

    model: Any = cp_model.CpModel()
    room_variables = {
        room.id_key: _create_room_variables(model, problem, room)
        for room in problem.rooms
    }

    model.AddNoOverlap2D(
        [variables.x_interval for variables in room_variables.values()],
        [variables.y_interval for variables in room_variables.values()],
    )

    return ModelContext(
        model=model,
        problem=problem,
        profile=profile,
        room_variables=room_variables,
    )


def _bounded_constraint(
    model: Any,
    variable: Any,
    lower: int,
    upper: int,
    presence: Any,
) -> None:
    model.Add(variable >= min(lower, upper)).OnlyEnforceIf(presence)
    model.Add(variable <= max(lower, upper)).OnlyEnforceIf(presence)


def apply_seed_policy(context: ModelContext) -> None:
    seed = context.problem.seed
    policy = context.profile.seed
    if seed is None:
        return

    scale = context.problem.scale
    floor = context.problem.floor
    position_delta = (
        scale.minimum_length(policy.position_tolerance)
        if policy.position_tolerance is not None
        else None
    )
    size_delta = (
        scale.minimum_length(policy.size_tolerance)
        if policy.size_tolerance is not None
        else None
    )

    for room_id_key, room_seed in seed.rooms.items():
        variables = context.room_variables.get(room_id_key)
        if variables is None:
            continue
        room = variables.room

        if policy.force_seeded_rooms_present:
            context.model.Add(variables.present == 1)

        if policy.apply_hints:
            context.model.AddHint(variables.present, 1)
            context.model.AddHint(variables.x, room_seed.x)
            context.model.AddHint(variables.y, room_seed.y)
            if room_seed.width is not None:
                context.model.AddHint(variables.width, room_seed.width)
            if room_seed.height is not None:
                context.model.AddHint(variables.height, room_seed.height)

        if position_delta is not None:
            _bounded_constraint(
                context.model,
                variables.x,
                max(0, room_seed.x - position_delta),
                min(floor.width - room.min_width, room_seed.x + position_delta),
                variables.present,
            )
            _bounded_constraint(
                context.model,
                variables.y,
                max(0, room_seed.y - position_delta),
                min(floor.height - room.min_height, room_seed.y + position_delta),
                variables.present,
            )

        if size_delta is not None and room_seed.width is not None:
            _bounded_constraint(
                context.model,
                variables.width,
                max(room.min_width, room_seed.width - size_delta),
                min(room.max_width, room_seed.width + size_delta),
                variables.present,
            )
        if size_delta is not None and room_seed.height is not None:
            _bounded_constraint(
                context.model,
                variables.height,
                max(room.min_height, room_seed.height - size_delta),
                min(room.max_height, room_seed.height + size_delta),
                variables.present,
            )
