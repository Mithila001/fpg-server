from __future__ import annotations

import math

from shapely.geometry import Polygon as ShapelyPolygon

from app.algorithms.buildable_land.geometry import geometry_tolerance
from app.algorithms.types_new import (
    BuildableLand,
    BuildableSpaceErrorCode,
    NormalizedLand,
    UsableLand,
    UsableLandConstraints,
)
from app.core.execution import ExecutionContext

from .exceptions import UsableLandError
from .logging import UsableLandEvent, log_usable_land_event
from .search import find_best_local_rectangle
from .transform import build_road_aligned_transform


def find_usable_land(
    buildable_land: BuildableLand,
    land: NormalizedLand,
    constraints: UsableLandConstraints,
    *,
    context: ExecutionContext | None = None,
) -> UsableLand:
    log_usable_land_event(
        context,
        UsableLandEvent.SEARCH_STARTED,
        payload={
            "minimum_width": constraints.minimum_width,
            "minimum_length": constraints.minimum_length,
            "search_resolution": constraints.search_resolution,
        },
    )
    try:
        transform = build_road_aligned_transform(land)
        local_buildable = transform.to_local_polygon(buildable_land.boundary)
        candidate, evaluated = find_best_local_rectangle(
            local_buildable,
            constraints,
        )
        log_usable_land_event(
            context,
            UsableLandEvent.CANDIDATES_EVALUATED,
            payload={"candidate_pairs_evaluated": evaluated},
        )

        tolerance = geometry_tolerance(local_buildable.points)
        buildable_shape = ShapelyPolygon(
            [(point.x, point.y) for point in local_buildable.points]
        )
        candidate_shape = ShapelyPolygon(
            [(point.x, point.y) for point in candidate.polygon.points]
        )
        if (
            not candidate_shape.is_valid
            or candidate_shape.area <= 0
            or not buildable_shape.buffer(tolerance).covers(candidate_shape)
            or not math.isclose(
                candidate_shape.area,
                candidate.area,
                rel_tol=1e-9,
                abs_tol=tolerance,
            )
        ):
            raise UsableLandError(
                BuildableSpaceErrorCode.USABLE_LAND_CALCULATION_FAILED,
                "The selected usable rectangle failed final geometry validation.",
            )

        world_boundary = transform.to_world_polygon(candidate.polygon)
        if any(
            not math.isfinite(point.x) or not math.isfinite(point.y)
            for point in world_boundary.points
        ):
            raise UsableLandError(
                BuildableSpaceErrorCode.USABLE_LAND_CALCULATION_FAILED,
                "The selected usable rectangle has non-finite coordinates.",
            )
        result = UsableLand(
            boundary=world_boundary,
            width=candidate.width,
            length=candidate.length,
            area=candidate.area,
            floor_width_alignment=candidate.alignment,
            entry_road_edge_index=land.main_entry_road.boundary_edge_index,
        )
        log_usable_land_event(
            context,
            UsableLandEvent.FOUND,
            payload={
                "usable_land_area": result.area,
                "usable_width": result.width,
                "usable_length": result.length,
                "floor_width_alignment": result.floor_width_alignment.value,
            },
        )
        return result
    except UsableLandError as exc:
        event = (
            UsableLandEvent.NOT_FOUND
            if exc.code is BuildableSpaceErrorCode.NO_USABLE_LAND_FOUND
            else UsableLandEvent.SEARCH_FAILED
        )
        log_usable_land_event(
            context,
            event,
            level="ERROR",
            payload={"error_code": exc.code.value, **exc.details},
            exception=exc,
        )
        raise
    except (ArithmeticError, StopIteration, ValueError) as exc:
        wrapped = UsableLandError(
            BuildableSpaceErrorCode.USABLE_LAND_CALCULATION_FAILED,
            "Usable-land geometry calculation failed.",
        )
        log_usable_land_event(
            context,
            UsableLandEvent.SEARCH_FAILED,
            level="ERROR",
            payload={"error_code": wrapped.code.value},
            exception=exc,
        )
        raise wrapped from exc
