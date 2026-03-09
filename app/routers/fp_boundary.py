from fastapi import APIRouter
from app.algorithms.fp_boundary_finder import FPBoundaryFinder
from app.schemas.fp_boundary_schemas import (
    FPBoundaryRequest,
    FPBoundaryResponse,
    FPBoundaryMockResponse,
)
from app.mock_data.mock_lands import MOCK_LANDS

router = APIRouter(prefix="/fp-boundary", tags=["FP Boundary Finder"])


@router.post("/run", response_model=FPBoundaryResponse)
def run_fp_boundary(request: FPBoundaryRequest):
    """
    Run the FP Boundary Finder on a single polygon.

    Returns three polygon representations:
    - `final_polygon`: the supplied polygon in world coordinates
    - `rect_parallel`: largest inscribed rectangle aligned to the first edge
    - `rect_perpendicular`: largest inscribed rectangle perpendicular to the first edge
    """
    try:
        finder = FPBoundaryFinder()
        final_polygon, rect_parallel, rect_perpendicular = finder.fp_boundary_finder(
            polygon_coordinates=request.polygon_coordinates,
            min_width=request.min_width,
            min_height=request.min_height,
        )
        return FPBoundaryResponse(
            final_polygon=final_polygon,
            rect_parallel=rect_parallel,
            rect_perpendicular=rect_perpendicular,
        )
    except Exception as exc:
        return FPBoundaryResponse(
            final_polygon=[],
            rect_parallel=[],
            rect_perpendicular=[],
            error=str(exc),
        )


@router.post("/run-mock", response_model=FPBoundaryMockResponse)
def run_fp_boundary_mock():
    """
    Run the FP Boundary Finder on all MOCK_LANDS entries.

    Returns one result per mock land entry.
    """
    results = []
    for land_entry in MOCK_LANDS:
        coords = land_entry["land_coordinates"]
        try:
            finder = FPBoundaryFinder()
            final_polygon, rect_parallel, rect_perpendicular = finder.fp_boundary_finder(
                polygon_coordinates=coords,
                min_width=5.0,
                min_height=0.5,
            )
            results.append(
                FPBoundaryResponse(
                    final_polygon=final_polygon,
                    rect_parallel=rect_parallel,
                    rect_perpendicular=rect_perpendicular,
                )
            )
        except Exception as exc:
            results.append(
                FPBoundaryResponse(
                    final_polygon=[],
                    rect_parallel=[],
                    rect_perpendicular=[],
                    error=str(exc),
                )
            )

    return FPBoundaryMockResponse(results=results, total=len(results))
