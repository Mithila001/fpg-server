from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.fpg_rooms.config_fpg import DEFAULT_SOLVER_MAX_TIME_SECONDS

from .constraint_control_panel import ConstraintControlPanel
from .fpgr_core import FpgrCore
from ..types import FpgRequirements


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
    """Profile 2 (refine): seeded bounded solve focused on refinement soft features."""
    if not initial_rooms:
        return RefineResult(
            solved=False,
            rooms=[],
            status="SKIPPED",
            message="Refine skipped because initial layout is empty",
        )

    control_panel = ConstraintControlPanel.refine_profile_1()
    core = FpgrCore(requirements, control_panel=control_panel)
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
