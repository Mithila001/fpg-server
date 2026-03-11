"""app/dev/routes.py  —  DEV-ONLY endpoints.

These routes are for front-end integration testing during development and are
NOT intended for production deployment.  The router is registered in
app/main.py under the "/dev" prefix and carries a "dev" tag so it is easily
identifiable (and removable) later.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get(
    "/floor-plan",
    summary="[DEV] Generate a floor plan and return cleaned wall layout",
    response_class=JSONResponse,
)
def get_floor_plan():
    """Generate a floor plan using the default DB template and return the
    cleaned wall-coordinate layout suitable for front-end rendering.

    Response shape::

        {
            "walls": [
                {"start": [x1, y1], "end": [x2, y2]},
                ...
            ],
            "rooms": [
                {"name": "bedroom1", "type": "bedroom", "center": [cx, cy]},
                ...
            ]
        }

    Each ``walls`` entry represents one unique wall segment.  Shared walls
    between adjacent rooms appear only once.  ``rooms`` entries carry the room
    identifier and the centre coordinate for label placement.
    """
    from app.services.algorithm_manager import apiTest

    walls, rooms = apiTest()

    if not walls and not rooms:
        raise HTTPException(
            status_code=500,
            detail="Floor plan generation failed or no template found in database.",
        )

    return {
        "walls": [
            {"start": list(wall[0]), "end": list(wall[1])}
            for wall in walls
        ],
        "rooms": [
            {
                "name": room["name"],
                "type": room["type"],
                "center": list(room["center"]),
            }
            for room in rooms
        ],
    }


@router.get(
    "/formatter-floor-plan",
    summary="[DEV] Generate a floor plan and return wall layout via FpFormatter",
    response_class=JSONResponse,
)
def get_formatter_floor_plan():
    """Generate a floor plan using the DB template and run the new formatter.

    This endpoint exercises the ``FpFormatter`` code.  The output schema is
    identical to :func:`get_floor_plan` but the cleaning algorithm differs.
    """
    from app.services.algorithm_manager import apiFormatter

    walls, rooms = apiFormatter()

    if not walls and not rooms:
        raise HTTPException(
            status_code=500,
            detail="Floor plan generation failed or no template found in database.",
        )

    return {
        "walls": [
            {"start": list(wall[0]), "end": list(wall[1])}
            for wall in walls
        ],
        "rooms": [
            {
                "name": room["name"],
                "type": room["type"],
                "center": list(room["center"]),
            }
            for room in rooms
        ],
    }


@router.get(
    "/raw-floor-plan",
    summary="[DEV] Generate a floor plan and return raw room polygons",
    response_class=JSONResponse,
)
def get_raw_floor_plan():
    """Return the raw polygon list produced by :func:`run_fpg` without any
    post-processing.  Useful for comparison or debugging the cleaning logic.

    Response shape::

        {
            "polygons": [
                [[x1,y1],[x2,y2],[x3,y3],[x4,y4]],
                ...
            ],
            "rooms": [
                {"name": ..., "type": ..., "center": [cx,cy]},
                ...
            ]
        }

    Room centres are computed in the same manner as :func:`apiTest` but no
    wall merging is performed.
    """
    from app.services.algorithm_manager import run_fpg

    polygons, generator = run_fpg()

    # compute room metadata exactly as apiTest does but omit cleaning
    rooms = []
    if generator is not None:
        try:
            solver_rooms = generator.get_solution()
        except Exception:
            solver_rooms = []
    else:
        solver_rooms = []

    while len(solver_rooms) < len(polygons):
        solver_rooms.append({})

    for idx, poly in enumerate(polygons):
        sr = solver_rooms[idx]
        name = sr.get("name") or f"room_{idx}"
        rtype = sr.get("type", "")
        if sr.get("x") is not None and sr.get("w") is not None:
            cx = float(sr["x"]) + float(sr["w"]) / 2.0
            cy = float(sr["y"]) + float(sr["h"]) / 2.0
            center = [cx, cy]
        else:
            # simple centroid
            n = len(poly)
            if n:
                cx = sum(p[0] for p in poly) / n
                cy = sum(p[1] for p in poly) / n
            else:
                cx = cy = 0.0
            center = [cx, cy]
        rooms.append({"name": name, "type": rtype, "center": center})

    return {"polygons": polygons, "rooms": rooms}


@router.get(
    "/validate-floor-plan",
    summary="[DEV] Run both raw and cleaned layouts and return diagnostics",
    response_class=JSONResponse,
)
def validate_floor_plan():
    """Produce a diagnostic report useful for comparing raw and cleaned data.

    The response is the dictionary returned by
    :func:`app.util.layout_coordinates_clean_up.validate_layout`, described in
    that module's docstring.  In addition to counts and ``merged_edges`` the
    report now includes an ``overlaps`` list, with colinear segments that
    partially overlap but were not merged.  This helps pinpoint the "messy"
    walls you observed when adjacent room edges share only part of their
    lengths.
    """
    from app.services.algorithm_manager import run_fpg
    from app.util.layout_coordinates_clean_up import validate_layout

    polygons, generator = run_fpg()
    report = validate_layout(polygons, generator)
    return report
