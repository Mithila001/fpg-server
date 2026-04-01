from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.fpg_rooms.config_fpg import DEFAULT_SOLVER_MAX_TIME_SECONDS

from .fpgr_core import FpgrCore
from .types.room import FpgRequirements


@dataclass
class RefineResult:
    solved: bool
    rooms: list[dict[str, Any]]
    status: str
    message: str


def run_refine_profile_1(
    requirements: FpgRequirements,
    initial_rooms: list[dict[str, Any]],
    wiggle_room: int = 10,
    verbose: bool = False,
) -> RefineResult:
    """Profile 2 (refine): seeded bounded solve focused on Constraints A/B/C/D."""
    if not initial_rooms:
        return RefineResult(
            solved=False,
            rooms=[],
            status="SKIPPED",
            message="Refine skipped because initial layout is empty",
        )

    core = FpgrCore(requirements)
    solved = core.solve(
        seed_layout=initial_rooms,
        wiggle_room=wiggle_room,
        include_constraint_b_soft=True,
        include_constraint_a_soft=True,
        include_constraint_c_soft=True,
        include_constraint_d_soft=True,
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
