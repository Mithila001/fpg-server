# from __future__ import annotations

# from fastapi import APIRouter, Header, HTTPException, Request
# from pydantic import BaseModel, Field

# router = APIRouter(prefix="/algorithms", tags=["algorithms"])


# class CoordinatePayload(BaseModel):
#     x: float
#     y: float


# class RoadConnectedPayload(BaseModel):
#     segment: list[CoordinatePayload] = Field(default_factory=list)
#     roadType: str | None = None


# class BuildableSpaceRequest(BaseModel):
#     area: float
#     segmentsCoordinates: list[CoordinatePayload] = Field(min_length=3)
#     roadConnected: list[RoadConnectedPayload] = Field(default_factory=list)
#     min_width: float = 100
#     min_height: float = 100
#     should_plot: bool = False


# class JobSubmitResponse(BaseModel):
#     job_id: str
#     status: str
#     message: str


# def _resolve_client_key(request: Request, x_client_id: str | None) -> str:
#     if x_client_id and x_client_id.strip():
#         return x_client_id.strip()
#     return request.client.host if request.client else "unknown"


# @router.post("/buildable-space", response_model=JobSubmitResponse, status_code=202)
# def submit_buildable_space(
#     request: Request,
#     body: BuildableSpaceRequest,
#     x_client_id: str | None = Header(default=None),
# ):
#     client_key = _resolve_client_key(request, x_client_id)
#     submission = job_registry.submit_job(
#         job_kind=JobKind.BUILDABLE_SPACE,
#         client_key=client_key,
#         request_payload=body.model_dump(),
#     )
#     if not submission["accepted"]:
#         raise HTTPException(
#             status_code=409,
#             detail=submission["message"],
#         )
#     return JobSubmitResponse(**submission)
