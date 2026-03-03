from fastapi import APIRouter
from app.algorithms.usable_land_space_finder import UsableSpaceFinder
from app.schemas.usable_land_schemas import (
    UsableLandRequest,
    UsableLandResponse,
    UsableLandMockResponse,
)
from app.mock_data.mock_lands import MOCK_LANDS

router = APIRouter(prefix="/usable-land", tags=["Usable Land Space Finder"])


@router.post("/run", response_model=UsableLandResponse)
def run_usable_land(request: UsableLandRequest):
    """
    Compute the buildable/usable polygon from a land polygon and per-edge setbacks.

    - `vertices`: ordered (x, y) coordinates of the land boundary
    - `offsets`: setback distance for each edge (same length as vertices)
    """
    try:
        finder = UsableSpaceFinder()
        buildable_vertices = finder.find_buildable_space(
            vertices=request.vertices,
            offsets=request.offsets,
        )
        return UsableLandResponse(buildable_vertices=buildable_vertices)
    except Exception as exc:
        return UsableLandResponse(buildable_vertices=[], error=str(exc))


@router.post("/run-mock", response_model=UsableLandMockResponse)
def run_usable_land_mock():
    """
    Run the Usable Land Space Finder on all MOCK_LANDS entries.

    Returns one result per mock land entry.
    """
    results = []
    for land_entry in MOCK_LANDS:
        coords = land_entry["land_coordinates"]
        offsets = land_entry["setbacksValues"]
        try:
            finder = UsableSpaceFinder()
            buildable_vertices = finder.find_buildable_space(
                vertices=coords,
                offsets=offsets,
            )
            results.append(UsableLandResponse(buildable_vertices=buildable_vertices))
        except Exception as exc:
            results.append(UsableLandResponse(buildable_vertices=[], error=str(exc)))

    return UsableLandMockResponse(results=results, total=len(results))
