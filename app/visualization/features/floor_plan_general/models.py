from __future__ import annotations

from dataclasses import dataclass

from fpg_core.types_new import FloorPlan


@dataclass(frozen=True, slots=True)
class FloorPlanVisualizationStage:
    """One ordered floor-plan snapshot in the generation flow."""

    stage_id: str
    stage_name: str
    category: str
    profile_name: str | None
    floor_plan: FloorPlan

    def __post_init__(self) -> None:
        if not self.stage_id.strip():
            raise ValueError("stage_id cannot be empty")
        if not self.stage_name.strip():
            raise ValueError("stage_name cannot be empty")
        if not self.category.strip():
            raise ValueError("category cannot be empty")
        if self.profile_name is not None and not self.profile_name.strip():
            raise ValueError("profile_name cannot be blank when provided")
        if not isinstance(self.floor_plan, FloorPlan):
            raise TypeError("floor_plan must be a types_new.FloorPlan instance")
        if len(self.floor_plan.boundary.points) < 3:
            raise ValueError("floor_plan boundary must contain at least three points")

        for room in self.floor_plan.rooms:
            if len(room.boundary.points) < 3:
                raise ValueError(
                    f"room {room.id!s} boundary must contain at least three points"
                )


@dataclass(frozen=True, slots=True)
class FloorPlanFlowVisualization:
    """Ordered floor-plan stages rendered into one combined image."""

    stages: tuple[FloorPlanVisualizationStage, ...]

    def __post_init__(self) -> None:
        if not self.stages:
            raise ValueError("stages must contain at least one floor-plan stage")

        stage_ids: set[str] = set()
        for stage in self.stages:
            if not isinstance(stage, FloorPlanVisualizationStage):
                raise TypeError(
                    "every stages entry must be a FloorPlanVisualizationStage"
                )
            if stage.stage_id in stage_ids:
                raise ValueError(f"duplicate stage_id: {stage.stage_id}")
            stage_ids.add(stage.stage_id)
