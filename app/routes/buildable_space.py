from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fpg_core.domain import (
    BuildableSpaceErrorCode,
    BuildableSpaceRequestData,
    BuildableSpaceStage,
    FloorWidthAlignment,
    Point,
    Polygon,
    RoadAttachment,
    RoadRole,
    RoadType,
)
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from starlette.responses import Response

from app.artifacts import ArtifactStorage
from app.core.execution import ExecutionContext
from app.core_config import get_server_config
from app.pipeline.buildable_space import BuildableSpacePipelineError
from app.routes.errors import ApiErrorResponse, api_error_response
from app.services.buildable_space_service import execute_buildable_space

router = APIRouter(prefix="/api/v1", tags=["buildable-space"])
BUILDABLE_SPACE_PATH = "/api/v1/buildable-space"


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LandPointRequest(_ContractModel):
    x: StrictInt
    y: StrictInt


class LandBoundaryRequest(_ContractModel):
    points: list[LandPointRequest] = Field(min_length=4)


class RoadAttachmentRequest(_ContractModel):
    boundary_edge_index: StrictInt = Field(ge=0)
    role: RoadRole
    road_type: RoadType


class BuildableSpaceRequest(_ContractModel):
    land_boundary: LandBoundaryRequest
    roads: list[RoadAttachmentRequest] = Field(min_length=1)


class PointResponse(_ContractModel):
    x: float
    y: float


class PolygonResponse(_ContractModel):
    points: list[PointResponse]


class UnitsResponse(_ContractModel):
    project_units_per_meter: int


class OriginalLandResponse(_ContractModel):
    area: float


class EdgeSetbackResponse(_ContractModel):
    edge_index: int
    side: str
    base_setback: int
    road_adjustment: int
    final_setback: int
    road_type: RoadType | None = None


class BuildableLandResponse(_ContractModel):
    boundary: PolygonResponse
    area: float
    edge_setbacks: list[EdgeSetbackResponse]


class UsableLandResponse(_ContractModel):
    boundary: PolygonResponse
    width: int
    length: int
    area: int
    floor_width_alignment: FloorWidthAlignment
    entry_road_edge_index: int


class BuildableSpaceResponse(_ContractModel):
    flow_id: str
    units: UnitsResponse
    original_land: OriginalLandResponse
    buildable_land: BuildableLandResponse
    usable_land: UsableLandResponse
    reference_profile: str


def _ensure_execution_context(request: Request) -> ExecutionContext:
    existing = getattr(request.state, "buildable_space_execution_context", None)
    if isinstance(existing, ExecutionContext):
        return existing
    try:
        context = ArtifactStorage().create_execution_context()
    except Exception:
        context = ExecutionContext.create_root()
    request.state.buildable_space_execution_context = context
    return context


async def buildable_space_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.url.path != BUILDABLE_SPACE_PATH or request.method != "POST":
        return await call_next(request)

    context = _ensure_execution_context(request)
    flow_id = str(context.flow_id)
    try:
        response = await call_next(request)
    except Exception:
        response = api_error_response(
            status_code=500,
            stage=BuildableSpaceStage.RESPONSE.value,
            code=BuildableSpaceErrorCode.UNEXPECTED_BUILDABLE_SPACE_ERROR.value,
            message="Buildable-space calculation failed unexpectedly.",
        )
    response.headers["X-Flow-ID"] = flow_id
    return response


def _to_service_request(body: BuildableSpaceRequest) -> BuildableSpaceRequestData:
    return BuildableSpaceRequestData(
        land_boundary=Polygon(
            tuple(Point(point.x, point.y) for point in body.land_boundary.points)
        ),
        roads=tuple(
            RoadAttachment(
                boundary_edge_index=road.boundary_edge_index,
                role=road.role,
                road_type=road.road_type,
            )
            for road in body.roads
        ),
    )


def _polygon_response(polygon: Polygon) -> PolygonResponse:
    return PolygonResponse(
        points=[PointResponse(x=point.x, y=point.y) for point in polygon.points]
    )


@router.post(
    "/buildable-space",
    response_model=BuildableSpaceResponse,
    responses={
        422: {"model": ApiErrorResponse},
        500: {"model": ApiErrorResponse},
    },
)
def buildable_space(
    body: BuildableSpaceRequest,
    request: Request,
) -> BuildableSpaceResponse | JSONResponse:
    context = _ensure_execution_context(request)
    flow_id = str(context.flow_id)
    try:
        result = execute_buildable_space(
            _to_service_request(body),
            core_config=get_server_config(request.app).core,
            execution_context=context,
        )
    except BuildableSpacePipelineError as exc:
        status_code = (
            500
            if exc.code
            in {
                BuildableSpaceErrorCode.REFERENCE_DATA_ERROR,
                BuildableSpaceErrorCode.UNEXPECTED_BUILDABLE_SPACE_ERROR,
            }
            else 422
        )
        return api_error_response(
            status_code=status_code,
            stage=exc.stage.value,
            code=exc.code.value,
            message=exc.message,
            details=dict(exc.details),
        )
    except Exception:
        return api_error_response(
            status_code=500,
            stage=BuildableSpaceStage.RESPONSE.value,
            code=BuildableSpaceErrorCode.UNEXPECTED_BUILDABLE_SPACE_ERROR.value,
            message="Buildable-space calculation failed unexpectedly.",
        )

    buildable = result.buildable_land
    usable = result.usable_land
    return BuildableSpaceResponse(
        flow_id=flow_id,
        units=UnitsResponse(project_units_per_meter=result.project_units_per_meter),
        original_land=OriginalLandResponse(area=result.original_land_area),
        buildable_land=BuildableLandResponse(
            boundary=_polygon_response(buildable.boundary),
            area=buildable.area,
            edge_setbacks=[
                EdgeSetbackResponse(
                    edge_index=item.edge_index,
                    side=item.side.value,
                    base_setback=item.base_setback,
                    road_adjustment=item.road_adjustment,
                    final_setback=item.final_setback,
                    road_type=item.road_type,
                )
                for item in buildable.edge_setbacks
            ],
        ),
        usable_land=UsableLandResponse(
            boundary=_polygon_response(usable.boundary),
            width=usable.width,
            length=usable.length,
            area=usable.area,
            floor_width_alignment=usable.floor_width_alignment,
            entry_road_edge_index=usable.entry_road_edge_index,
        ),
        reference_profile=result.reference_profile,
    )
