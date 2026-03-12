from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.algorithm_manager import quicklyRunWithDbData
from app.algorithms.fp_formatter_for_frontend.fp_wall_formatter import FpFormatter


class FormatterResponse(BaseModel):
    """Response returned by the formatter endpoint.

    FastAPI/Pydantic will convert the float keys of the inner dictionaries to
    strings in the JSON output because JSON object keys must be strings.  The
    frontend should be prepared for that behaviour.
    """

    merged_horiz: Dict[str, Any]
    merged_vert: Dict[str, Any]


router = APIRouter(prefix="/algorithms", tags=["algorithms"])


@router.get("/format", response_model=FormatterResponse)
def get_formatted_layout():
    """Run the DB-backed generator, format the polygon output, and return it.

    This endpoint mirrors the behaviour of the debug helper used during
    development.  No input is required; the room definitions are pulled from
    the first record found in the ``room_setup_template`` table.  If the
    database contains no template the route raises a 404 so that callers can
    distinguish the "no data yet" situation from a successful run.
    """

    polygons, generator = quicklyRunWithDbData()
    if generator is None:
        # nothing in the database
        raise HTTPException(status_code=404, detail="no room template available")

    fmt = FpFormatter()
    merged_horiz, merged_vert = fmt.fpFormatter(polygons)

    # Pydantic expects dict keys to be strings; our formatter returns float
    # keys, so convert them now.  JSON output will naturally have string keys
    # anyway.
    def _stringify_keys(d: dict) -> dict:
        return {str(k): v for k, v in d.items()}

    return FormatterResponse(
        merged_horiz=_stringify_keys(merged_horiz),
        merged_vert=_stringify_keys(merged_vert),
    )
