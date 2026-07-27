from __future__ import annotations

from time import perf_counter

from app.algorithms.buildable_land import (
    BuildableLandError,
    calculate_buildable_land,
    normalize_land_request,
)
from app.algorithms.buildable_land.geometry import polygon_area
from app.algorithms.types_new import (
    BuildableSpaceErrorCode,
    BuildableSpaceRequestData,
    BuildableSpaceResult,
    BuildableSpaceStage,
)
from app.algorithms.usable_land import UsableLandError, find_usable_land
from app.core.execution import PipelineStage

from .context import BuildableSpaceContext
from .exceptions import BuildableSpacePipelineError, ReferenceDataError
from .logging import BuildableSpaceEvent, log_buildable_space_event
from .reference_data import load_buildable_space_reference_data


def run_buildable_space_pipeline(
    request: BuildableSpaceRequestData,
    context: BuildableSpaceContext,
) -> BuildableSpaceResult:
    started = perf_counter()
    execution = context.execution_context
    log_buildable_space_event(execution, BuildableSpaceEvent.STARTED)
    try:
        try:
            reference_data = load_buildable_space_reference_data()
        except ReferenceDataError as exc:
            raise BuildableSpacePipelineError(
                BuildableSpaceStage.REFERENCE_DATA,
                BuildableSpaceErrorCode.REFERENCE_DATA_ERROR,
                "Buildable-space reference data is unavailable.",
            ) from exc
        context = context.with_reference_profile(reference_data.active_profile.name)
        reference_execution = execution.with_stage(PipelineStage.REFERENCE_DATA)
        log_buildable_space_event(
            reference_execution,
            BuildableSpaceEvent.REFERENCE_DATA_LOADED,
            payload={
                "reference_profile": context.reference_profile,
                "schema_version": reference_data.schema_version,
            },
        )

        try:
            land = normalize_land_request(request, reference_data)
        except BuildableLandError as exc:
            raise BuildableSpacePipelineError(
                BuildableSpaceStage.REQUEST_VALIDATION,
                exc.code,
                exc.message,
            ) from exc
        validation_execution = execution.with_stage(PipelineStage.REQUEST_VALIDATION)
        common: dict[str, object] = {
            "reference_profile": context.reference_profile,
            "land_vertex_count": len(land.boundary.points),
            "main_entry_edge_index": land.main_entry_road.boundary_edge_index,
            "road_type": land.main_entry_road.road_type.value,
        }
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
            buildable_land = calculate_buildable_land(
                land,
                reference_data.active_profile,
                context=execution.with_stage(PipelineStage.BUILDABLE_LAND),
            )
        except BuildableLandError as exc:
            raise BuildableSpacePipelineError(
                BuildableSpaceStage.BUILDABLE_LAND,
                exc.code,
                exc.message,
            ) from exc

        try:
            usable_land = find_usable_land(
                buildable_land,
                land,
                reference_data.usable_land_constraints,
                context=execution.with_stage(PipelineStage.USABLE_LAND),
            )
        except UsableLandError as exc:
            raise BuildableSpacePipelineError(
                BuildableSpaceStage.USABLE_LAND,
                exc.code,
                exc.message,
                exc.details,
            ) from exc

        result = BuildableSpaceResult(
            original_land_area=polygon_area(land.boundary),
            buildable_land=buildable_land,
            usable_land=usable_land,
            reference_profile=reference_data.active_profile.name,
            project_units_per_meter=reference_data.project_units_per_meter,
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
