from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from time import time

from app.algorithms.fpg_rooms.fpg_optuna.exceptions import TrialTimeoutError
from app.services.algorithm_manager_v2 import run_fpg_pipeline_api
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.util.tracking import use_tracking_context
from app.util.unit_converter import (
    converter_cm_to_unit,
    converter_unit_to_centimeters,
)
from app.util.room_requirements import floor_values
# Plotting hook removed so api_result_plotter is isolated and unused by default
# from test.dev.plotter_loader import plot_floor_plan_payload
# from app.util.logger import SystemLogger

# In-memory per-client rate limit tracker (simple, single-process)
_last_format_request: dict[str, float] = {}
_last_format_v2_request: dict[str, float] = {}
_rate_limit_seconds = 2


class FormatterResponse(BaseModel):
    status: str
    message: str
    union_results: dict | None = None



class FormatterV2ApiRequest(BaseModel):
    floor_width: float
    floor_height: float
    room_template: RoomSetupTemplateBase
    should_optuna_run: bool = False
    optuna_trial_count: int = 20


router = APIRouter(prefix="/algorithms", tags=["algorithms"])


@router.post("/format/v2", response_model=FormatterResponse)
def get_formatted_layout_v2(request: Request, body: FormatterV2ApiRequest):
    """Run v2 API pipeline from request payload with simple per-client rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    now = time()
    last_call = _last_format_v2_request.get(client_ip, 0)
    elapsed = now - last_call
    if elapsed < _rate_limit_seconds:
        retry_after = _rate_limit_seconds - elapsed
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after:.1f} seconds.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
    _last_format_v2_request[client_ip] = now

    try:
        with use_tracking_context():
            # Floor dimensions are converted from cm to units, then floored to integers
            floored_width = floor_values(converter_cm_to_unit(body.floor_width))
            floored_height = floor_values(converter_cm_to_unit(body.floor_height))

            payload = run_fpg_pipeline_api(
                floor_width=floored_width,
                floor_height=floored_height,
                room_template=body.room_template,
                should_optuna_run=body.should_optuna_run,
                optuna_trial_count=body.optuna_trial_count,
            )
        payload = converter_unit_to_centimeters(payload)

        # Plotting is disabled in this branch to keep api_result_plotter isolated.
        return FormatterResponse(**payload)
    except TrialTimeoutError as e:
        raise HTTPException(
            status_code=408,
            detail={
                "error": "trial_timeout",
                "message": str(e),
                "elapsed_time": e.elapsed_time,
                "timeout_seconds": e.timeout_seconds,
            },
        )
