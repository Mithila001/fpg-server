import os
from typing import Sequence, Tuple

from buildable_space_finder import FPBoundaryFinder
from usable_space_in_land_finder.usable_space_finder import (
    UsableSpaceFinder,  # noqa: F401  (imported for example/IDE discoverability)
)


from plotters.polygon_plotter import PolygonPlotter

Coordinate = Tuple[float, float]

# Realistic mock lands: each entry includes coordinates + explicit per-edge setbacks
# AI NOTE: Use these data, DO NOT MODIFY.
MOCK_LANDS: Sequence[dict] = [
    {
        "land_coordinates": [(15.0, 1.5), (16.5, 9.0), (10.5, 12.3), (3.9, 10.2)],
        "setbacksValues": [1, 0.5, 0.5, 2],
    },
    # {
    #     "land_coordinates": [(15.0, 1.5), (16.5, 9.0), (10.5, 12.3), (3.9, 10.2)],
    #     "setbacksValues": [10, 1.5, 2.0, 1.5],
    # },
    # {
    #     "land_coordinates": [(16.8, 0.9), (26.1, 12.0), (7.2, 12.0), (1.5, 9.0)],
    #     "setbacksValues": [1.8, 1.2, 1.8, 1.2],
    # },
    # {
    #     "land_coordinates": [(22.5, 11.1), (13.5, 18.0), (4.8, 18.0), (4.5, 0.9)],
    #     "setbacksValues": [2.0, 1.5, 2.0, 1.5],
    # },
    # {
    #     "land_coordinates": [(21.9, 12.0), (1.5, 12.0), (6.0, 0.9)],
    #     "setbacksValues": [1.5, 1.5, 1.5],
    # },
    # {
    #     "land_coordinates": [(21.0, 18.0), (9.0, 18.0), (6.0, 0.9)],
    #     "setbacksValues": [2.0, 1.5, 1.5],
    # },
]


def run_engine(coordinates: Sequence[Coordinate], setbacks: Sequence[float]):
    """Run stage-1 (buildable) then stage-2 (usable) and return both results.

    Returns: (buildable_polygon, usable_polygon, diagnostics)
    """
    # Stage 1 — largest-inscribed rectangles & canonical buildable polygon
    result = FPBoundaryFinder().fp_boundary_finder(
        list(coordinates), min_width=5.0, min_height=0.5
    )

    # `run_buildableSpaceFinder_algorithm` returns (final_polygon, rect_par, rect_perp)
    if not result or not isinstance(result, tuple):
        raise RuntimeError("buildable-space engine returned unexpected result")

    buildable_polygon, rect_par, rect_perp = result

    # Stage 2 — run usable-space finder on the buildable polygon with per-edge setbacks
    #
    # the project now exposes only the class-based interface
    # (`UsableSpaceFinder`).  the old module-level ``find_buildable_space``
    # helper has been removed from the public API, so we call the method
    # directly instead; this mirrors the style of FPBoundaryFinder.
    edge_count = len(buildable_polygon) if buildable_polygon else len(coordinates)
    # strict API: accept a single scalar (broadcast) or an explicit per-edge list matching edge_count
    if not setbacks:
        raise ValueError(
            "setbacks must be provided (single value or list matching polygon edges)"
        )
    if len(setbacks) == 1:
        per_edge_setbacks = [setbacks[0]] * edge_count
    elif len(setbacks) == edge_count:
        per_edge_setbacks = list(setbacks)
    else:
        raise ValueError(
            f"setbacks length ({len(setbacks)}) does not match polygon edge count ({edge_count}).\n"
            "Provide a single value or a list with one value per edge."
        )

    usable_polygon = []
    try:
        usable_polygon = UsableSpaceFinder().find_buildable_space(
            buildable_polygon or list(coordinates), per_edge_setbacks
        )
    except Exception as exc:
        # don't crash the whole batch — return what we have plus the error message
        print(f"Warning: usable-space engine failed: {exc}")

    diagnostics = {
        "rect_parallel": rect_par,
        "rect_perpendicular": rect_perp,
        "used_setbacks": per_edge_setbacks,
    }

    return buildable_polygon, usable_polygon, diagnostics


# if __name__ == "__main__":
#     quick_demo_usable()

if __name__ == "__main__":
    # Batch-run the two-stage pipeline on the MOCK_LANDS and save a combined plot

    base_dir = os.path.dirname(__file__)
    out_land_dir = os.path.join(base_dir, "results", "land")
    out_space_dir = os.path.join(base_dir, "results", "space")
    os.makedirs(out_land_dir, exist_ok=True)
    os.makedirs(out_space_dir, exist_ok=True)

    for idx, land_entry in enumerate(MOCK_LANDS, start=1):
        land = land_entry.get("land_coordinates")
        if land is None:
            raise ValueError(f"MOCK_LANDS entry #{idx} missing 'land_coordinates'")
        if not isinstance(land, (list, tuple)):
            raise TypeError(
                f"MOCK_LANDS entry #{idx} 'land_coordinates' must be list/tuple"
            )

        setbacks = land_entry.get("setbacksValues")
        if setbacks is None:
            raise ValueError(f"MOCK_LANDS entry #{idx} must include 'setbacksValues'")

        buildable, usable, diag = run_engine(land, setbacks)
        print("Buildable polygon:", buildable)
        print("Usable polygon:", usable)
        print("Diagnostics:", diag)

        plotter = PolygonPlotter()
        plotter.polygon_line_plotter_single(
            coordinates_list=[buildable, usable],
            show=True,
            title="Input Land (Red) vs Usable Space (Green)",
        )

    print("\nBatch complete.")
