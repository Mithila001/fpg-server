from __future__ import annotations

from .fpgr_core import FpgrCore
from .types.room import FpgRequirements


class FloorPlanGenerator:
    """Profile 1 (generate): build a fresh layout from requirements."""

    def __init__(self, requirements: FpgRequirements):
        self._core = FpgrCore(requirements)
        self.last_status: int | None = None
        self.last_status_name: str = "NOT_RUN"

    def generate(self) -> bool:
        solved = self._core.solve(
            seed_layout=None,
            wiggle_room=0,
            include_constraint_b_soft=False,
            debug_log=True,
        )
        self.last_status = self._core.last_status
        self.last_status_name = self._core.last_status_name
        return solved

    def get_solution(self) -> list[dict]:
        return self._core.get_solution()
