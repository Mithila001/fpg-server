import os
from typing import Sequence, Tuple, List, Optional, Union

from fp_boundary_finder import FPBoundaryFinder
from usable_land_space_finder.usable_land_space_finder import (
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
    {
        "land_coordinates": [(15.0, 1.5), (16.5, 9.0), (10.5, 12.3), (3.9, 10.2)],
        "setbacksValues": [10, 1.5, 2.0, 1.5],
    },
    {
        "land_coordinates": [(16.8, 0.9), (26.1, 12.0), (7.2, 12.0), (1.5, 9.0)],
        "setbacksValues": [1.8, 1.2, 1.8, 1.2],
    },
    {
        "land_coordinates": [(22.5, 11.1), (13.5, 18.0), (4.8, 18.0), (4.5, 0.9)],
        "setbacksValues": [2.0, 1.5, 2.0, 1.5],
    },
    {
        "land_coordinates": [(21.9, 12.0), (1.5, 12.0), (6.0, 0.9)],
        "setbacksValues": [1.5, 1.5, 1.5],
    },
    {
        "land_coordinates": [(21.0, 18.0), (9.0, 18.0), (6.0, 0.9)],
        "setbacksValues": [2.0, 1.5, 1.5],
    },
]


def run_engine(
    coordinates: Sequence[Coordinate], setbacks: Sequence[float]
) -> Tuple[
    List[Coordinate],  # usable/buildable boundary from stage‑1
    List[Coordinate],  # fp_boundary (final_rect_parallel) from stage‑2
    Optional[Union[str, dict]],  # diagnostics info or error message
]:
    """Run stage-1 (buildable) then stage-2 (usable) and return three values.

    * First element: polygon returned by the usable-space engine (a.k.a. buildable
      polygon).
    * Second element: the ``final_rect_parallel`` result from
      :class:`FPBoundaryFinder.fp_boundary_finder` (i.e. the chosen fp boundary).
    * Third element: optional diagnostics—either an error string when the first
      stage failed or a dictionary containing intermediate results.
    """

    # make local copies with concrete list types to satisfy the typed APIs
    diagnostics: Optional[Union[str, dict]] = None
    usable_land_boundary: List[Coordinate] = []
    try:
        usable_land_boundary = UsableSpaceFinder().find_buildable_space(
            list(coordinates), list(setbacks)
        )
    except Exception as exc:
        diagnostics = str(exc)
        # don't crash the whole batch — report the problem and continue
        print(f"Warning: usable-space engine failed: {exc}")

    # Stage 2: FP boundary finder already expects a list
    final_polygon, final_rect_parallel, final_rect_perpendicular = (
        FPBoundaryFinder().fp_boundary_finder(
            list(coordinates), min_width=5.0, min_height=0.5
        )
    )

    # select the element the user requested
    fp_boundary = final_rect_parallel

    diagnostics = {
        "usable_land_boundary": usable_land_boundary,
        "full_fp_boundary": (
            final_polygon,
            final_rect_parallel,
            final_rect_perpendicular,
        ),
    }

    return usable_land_boundary, fp_boundary, diagnostics


# if __name__ == "__main__":
#     quick_demo_usable()

if __name__ == "__main__":
    # Batch-run the two-stage pipeline on the MOCK_LANDS and save a combined plot

    base_dir = os.path.dirname(__file__)
    out_land_dir = os.path.join(base_dir, "results", "land")
    out_space_dir = os.path.join(base_dir, "results", "space")
    os.makedirs(out_land_dir, exist_ok=True)
    os.makedirs(out_space_dir, exist_ok=True)

    # gather all polygon sets for a single batch operation
    batch_polygons: List[Sequence[Sequence[Coordinate]]] = []
    batch_titles: List[str] = []

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

        buildable, fp_boundary, diag = run_engine(land, setbacks)
        print("Buildable polygon:", buildable)
        print("FP boundary polygon:", fp_boundary)
        print("Diagnostics:", diag)

        # add to batch lists
        batch_polygons.append([land, buildable, fp_boundary])
        batch_titles.append(f"Entry {idx}: Land vs Usable")

    # perform one batch plot after processing all entries
    plotter = PolygonPlotter()
    plotter.polygon_line_plotter_batch(
        polygons_batch=batch_polygons,
        batch_no=1,
        titles=batch_titles,
    )

    print("\nBatch complete.")
