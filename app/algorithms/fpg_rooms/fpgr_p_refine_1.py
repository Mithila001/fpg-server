from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.fpg_rooms.config_fpg import DEFAULT_SOLVER_MAX_TIME_SECONDS

from .constraint_control_panel import ConstraintControlPanel
from .fpgr_core import FpgrCore
from .types.room import FpgRequirements, RoomData


@dataclass
class RefineResult:
    solved: bool
    rooms: list[dict[str, Any]]
    status: str
    message: str


def _with_refine_extenders(requirements: FpgRequirements) -> FpgRequirements:
    cfg = requirements.config
    is_enabled = bool(getattr(cfg, "living_room_extender_refine_only_enabled", False))
    if not is_enabled:
        return requirements

    extender_count = max(0, int(getattr(cfg, "living_room_extender_count", 0)))
    if extender_count <= 0:
        return requirements

    floor_width = max(1, int(getattr(cfg, "floor_plan_width", 30)))
    floor_height = max(1, int(getattr(cfg, "floor_plan_height", 30)))

    rooms = list(requirements.rooms)
    existing_names = {room.name for room in rooms}

    for index in range(extender_count):
        name = f"livingRoomExtender_{index + 1}"
        if name in existing_names:
            continue
        rooms.append(
            RoomData(
                name=name,
                type="livingRoomExtender",
                min_w=1,
                min_h=1,
                max_w=floor_width,
                max_h=floor_height,
            )
        )
        existing_names.add(name)

    return FpgRequirements(
        rooms=rooms,
        config=requirements.config,
        relation_constraints=list(getattr(requirements, "relation_constraints", [])),
    )


def run_refine_profile_1(
    requirements: FpgRequirements,
    initial_rooms: list[dict[str, Any]],
    wiggle_room: int = 10,
    verbose: bool = False,
) -> RefineResult:
    """Profile 2 (refine): seeded bounded solve focused on refinement soft features."""
    if not initial_rooms:
        return RefineResult(
            solved=False,
            rooms=[],
            status="SKIPPED",
            message="Refine skipped because initial layout is empty",
        )

    control_panel = ConstraintControlPanel.refine_profile_1()
    requirements_with_extenders = _with_refine_extenders(requirements)
    core = FpgrCore(requirements_with_extenders, control_panel=control_panel)
    solved = core.solve(
        seed_layout=initial_rooms,
        wiggle_room=wiggle_room,
        max_time_seconds=max(1.0, float(DEFAULT_SOLVER_MAX_TIME_SECONDS)),
        debug_log=verbose,
    )

    if not solved:
        return RefineResult(
            solved=False,
            rooms=initial_rooms,
            status=core.last_status_name,
            message="Refine stage returned non-feasible status; keeping stage-1 layout",
        )

    return RefineResult(
        solved=True,
        rooms=core.get_solution(),
        status=core.last_status_name,
        message="Refine stage produced a feasible improved layout",
    )
