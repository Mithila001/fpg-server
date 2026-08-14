from __future__ import annotations

from time import perf_counter

from fpg_core.buildable_land import (
    BuildableLandConfig,
    BuildableLandError,
    BuildableLandInput,
    calculate_buildable_land,
)
from fpg_core.buildable_land.geometry import polygon_area
from fpg_core.config import FpgCoreConfig
from fpg_core.domain import (
    BuildableSpaceErrorCode,
    BuildableSpaceRequestData,
    BuildableSpaceResult,
    BuildableSpaceStage,
)
from fpg_core.usable_land import (
    UsableLandConfig,
    UsableLandError,
    UsableLandInput,
    find_usable_land,
)

from app.core.execution import PipelineStage

from .context import BuildableSpaceContext
from .exceptions import BuildableSpacePipelineError
from .logging import BuildableSpaceEvent, log_buildable_space_event


def run_buildable_space_pipeline(
    request: BuildableSpaceRequestData,
    context: BuildableSpaceContext,
    core_config: FpgCoreConfig,
) -> BuildableSpaceResult:
    started = perf_counter()
    execution = context.execution_context
    log_buildable_space_event(execution, BuildableSpaceEvent.STARTED)
    try:
        reference_data = core_config.buildable_space
        context = context.with_reference_profile(reference_data.active_profile.name)
        reference_execution = execution.with_stage(PipelineStage.REFERENCE_DATA)
        log_buildable_space_event(
            reference_execution,
            BuildableSpaceEvent.REFERENCE_DATA_LOADED,
            payload={
                "reference_profile": context.reference_profile,
                "schema_version": core_config.schema_version,
            },
        )

        try:
            buildable_execution = calculate_buildable_land(
                BuildableLandInput(
                    request=request,
                    config=BuildableLandConfig(
                        setback_profile=reference_data.active_profile,
                        validation_limits=reference_data.validation_limits,
                    ),
                )
            )
        except BuildableLandError as exc:
            raise BuildableSpacePipelineError(
                BuildableSpaceStage.BUILDABLE_LAND,
                exc.code,
                exc.message,
            ) from exc
        buildable_land = buildable_execution.result.buildable_land
        land = buildable_execution.result.normalized_land
        common: dict[str, object] = {
            "reference_profile": context.reference_profile,
            "land_vertex_count": len(land.boundary.points),
            "main_entry_edge_index": land.main_entry_road.boundary_edge_index,
            "road_type": land.main_entry_road.road_type.value,
        }
        validation_execution = execution.with_stage(PipelineStage.REQUEST_VALIDATION)
        log_buildable_space_event(
            validation_execution,
            BuildableSpaceEvent.REQUEST_NORMALIZED,
            payload=common,
        )
        log_buildable_space_event(
            validation_execution,
            BuildableSpaceEvent.REQUEST_VALIDATED,
            payload=common,
        )

        try:
            constraints = reference_data.usable_land_constraints
            usable_execution = find_usable_land(
                UsableLandInput(
                    buildable_land=buildable_land,
                    land=land,
                    config=UsableLandConfig.from_constraints(constraints),
                )
            )
        except UsableLandError as exc:
            raise BuildableSpacePipelineError(
                BuildableSpaceStage.USABLE_LAND,
                exc.code,
                exc.message,
                exc.details,
            ) from exc
        usable_land = usable_execution.result

        result = BuildableSpaceResult(
            original_land_area=polygon_area(land.boundary),
            buildable_land=buildable_land,
            usable_land=usable_land,
            reference_profile=reference_data.active_profile.name,
            project_units_per_meter=core_config.project_units_per_meter,
        )
        log_buildable_space_event(
            execution.with_stage(PipelineStage.RESPONSE),
            BuildableSpaceEvent.COMPLETED,
            payload={
                **common,
                "original_land_area": result.original_land_area,
                "buildable_land_area": result.buildable_land.area,
                "usable_land_area": result.usable_land.area,
                "usable_width": result.usable_land.width,
                "usable_length": result.usable_land.length,
                "floor_width_alignment": (
                    result.usable_land.floor_width_alignment.value
                ),
                "duration_ms": (perf_counter() - started) * 1000,
            },
        )
        return result
    except BuildableSpacePipelineError as exc:
        log_buildable_space_event(
            execution,
            BuildableSpaceEvent.FAILED,
            level="ERROR",
            payload={
                "stage": exc.stage.value,
                "error_code": exc.code.value,
                "duration_ms": (perf_counter() - started) * 1000,
            },
            exception=exc,
        )
        raise
    except Exception as exc:
        wrapped = BuildableSpacePipelineError(
            BuildableSpaceStage.RESPONSE,
            BuildableSpaceErrorCode.UNEXPECTED_BUILDABLE_SPACE_ERROR,
            "Buildable-space calculation failed unexpectedly.",
        )
        log_buildable_space_event(
            execution,
            BuildableSpaceEvent.FAILED,
            level="ERROR",
            payload={
                "stage": wrapped.stage.value,
                "error_code": wrapped.code.value,
                "duration_ms": (perf_counter() - started) * 1000,
            },
            exception=exc,
        )
        raise wrapped from exc
