from __future__ import annotations

from .fpgr_core import FpgrCore
from .constraint_control_panel import ConstraintControlPanel
from ..types import FpgRequirements
from .utils.point_hints_seed_layout import build_seed_layout_from_point_hints


class FloorPlanGenerator:
    """Profile 1 (generate): build a fresh layout from requirements."""

    def __init__(self, requirements: FpgRequirements):
        self._core = FpgrCore(
            requirements, control_panel=ConstraintControlPanel.generate_profile()
        )
        self.last_status: int | None = None
        self.last_status_name: str = "NOT_RUN"

    def generate(self) -> bool:
        seed_layout = build_seed_layout_from_point_hints(
            rooms=self._core.rooms,
            floor_plan_width=self._core.floor_plan_width,
            floor_plan_height=self._core.floor_plan_height,
            point_hints=self._core.requirements.initial_point_hints,
        )
        solved = self._core.solve(
            seed_layout=seed_layout or None,
            wiggle_room=0,
            debug_log=True,
        )
        self.last_status = self._core.last_status
        self.last_status_name = self._core.last_status_name
        return solved

    def get_solution(self) -> list[dict]:
        return self._core.get_solution()
