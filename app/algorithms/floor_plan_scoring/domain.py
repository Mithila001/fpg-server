"""Type-only seam to the draft shared floor-plan structures.

``Restructure_Data.floor_plan`` is deliberately not imported at runtime. Its
current internal absolute import makes it unsafe to import as a package, while
the scorer is required to remain isolated to this directory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from Restructure_Data.floor_plan import FloorPlan
    from Restructure_Data.floor_plan_spec import FloorPlanGenerationSpec
else:
    FloorPlan: TypeAlias = Any
    FloorPlanGenerationSpec: TypeAlias = Any

__all__ = ["FloorPlan", "FloorPlanGenerationSpec"]
