"""Main (two-stage pipeline demo)

Demonstrates the complete workflow:
1. Run buildable_space_finder on realistic mock land polygons
   → Plot results in ./results/land/
2. Pass buildable-space output to usable_space_in_land-finder (with setbacks)
   → Plot results in ./results/space/

Mock coordinates represent various realistic land scenarios:
- Rectangular suburban lot
- Irregular corner lot
- Narrow infill lot
- L-shaped lot
- Trapezoidal lot
"""

import os
from typing import Sequence, Tuple

from buildable_space_finder.main1 import run_buildableSpaceFinder_algorithm
from usable_space_in_land_finder.main2 import find_buildable_space


from plotters.polygon_plotter import PolygonPlotter

Coordinate = Tuple[float, float]

# Realistic mock lands: each entry includes coordinates + explicit per-edge setbacks
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
# NOTE: DEFAULT_SETBACKS removed — each land MUST include `setbacksValues` (or a single numeric value to broadcast). Keep input explicit and simple.


def run_engine(coordinates: Sequence[Coordinate], setbacks: Sequence[float]):
    """Run stage-1 (buildable) then stage-2 (usable) and return both results.

    Returns: (buildable_polygon, usable_polygon, diagnostics)
    """
    # Stage 1 — largest-inscribed rectangles & canonical buildable polygon
    result = run_buildableSpaceFinder_algorithm(list(coordinates))

    # `run_buildableSpaceFinder_algorithm` returns (final_polygon, rect_par, rect_perp)
    if not result or not isinstance(result, tuple):
        raise RuntimeError("buildable-space engine returned unexpected result")

    buildable_polygon, rect_par, rect_perp = result

    # Stage 2 — run usable-space finder on the buildable polygon with per-edge setbacks
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
        usable_polygon = find_buildable_space(
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


def quick_demo_usable():
    # Setup data
    land = [(15.0, 1.5), (16.5, 9.0), (10.5, 12.3), (3.9, 10.2)]
    setbacks = [0, 0.5, 2, 0.5]  # Example values

    # Run Stage 2
    usable_polygon = find_buildable_space(land, setbacks)

    # Plot and display (Red = Input, Green = Result)
    plotter = PolygonPlotter()
    plotter.polygon_line_plotter_single(
        coordinates_list=[land, usable_polygon],
        show=True,
        title="Input Land (Red) vs Usable Space (Green)",
    )


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

        # # Combined plot: original land, buildable-space (A), usable-space (B)
        # combined_plotter = PolygonPlotter(output_base_dir=out_space_dir)
        # polys = [list(land), buildable or [], usable or []]
        # title = f"Land #{idx} — buildable + usable"
        # fig_ax = combined_plotter.polygon_line_plotter_single(
        #     coordinates_list=polys, show=False, title=title
        # )
        # print(f"Combined image saved: {combined_plotter.last_saved_file}")

        # # Also save stage-1 (land + buildable) into results/land for traceability
        # stage1_plotter = PolygonPlotter(output_base_dir=out_land_dir)
        # stage1_plotter.polygon_line_plotter_single(
        #     coordinates_list=[list(land), buildable or []],
        #     show=False,
        #     title=f"Land #{idx} — buildable",
        # )
        # print(f"Stage-1 image saved: {stage1_plotter.last_saved_file}")

    print("\nBatch complete.")
