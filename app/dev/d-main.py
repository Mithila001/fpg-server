# ruff: noqa: E402  # path manipulation occurs before imports below
from collections.abc import Sequence
import os
import sys

# python app/dev/d-main.py floor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
# print(f"[d-main] SCRIPT_DIR={SCRIPT_DIR}")
# print(f"[d-main] ROOT={ROOT}")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.algorithms.floor_plan_generator import FloorPlanGenerator
from app.algorithms.floor_plan_generator.types.room import (
    RoomData,
    ConfigData,
    FpgRequirements,
)
from app.algorithms.floor_plan_generator.config import (
    FLOOR_WIDTH,
    FLOOR_HEIGHT,
    MIN_COVERAGE,
)
from app.algorithms.usable_land_space_finder.usable_land_space_finder import (
    UsableSpaceFinder,
)
from app.algorithms.fp_boundary_finder.fp_boundary_finder import FPBoundaryFinder

from app.dev.plotters import PolygonPlotter

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


# python app/dev/d-main.py floor
def run_floor(times: int = 1, show: bool = True) -> list[list[tuple[float, float]]]:
    """Generate and optionally plot one or more floor plans from the DB template.

    Args:
        times: how many independent runs to perform.
        show: if True, display (and save) the plot.

    Returns:
        A list of polygon lists, one per run.
    """
    # import here to avoid a circular import at module load time
    from app.services.algorithm_manager import devModRunFPG

    # accumulate polygons from each run; type inferred by Python
    results = []

    for run_index in range(1, times + 1):
        polygons, generator = devModRunFPG()

        # log coordinates and sizes for each room/polygon if generator exists
        if generator is not None:
            for idx, r in enumerate(generator.get_solution(), start=1):
                # r contains x, y, w, h along with name/type
                print(
                    f"run {run_index} polygon {idx}: x={r.get('x')} y={r.get('y')} w={r.get('w')} h={r.get('h')}"
                )

        if polygons and generator and show:
            plotter = PolygonPlotter(output_base_dir="./app/dev/outputs")
            # generator exposes floor dimensions already used during solve
            plotter.floor_plan_plot(
                rooms_list=generator.rooms,
                solver=generator.solver,
                LAND_WIDTH=generator.floor_plan_width,
                LAND_HEIGHT=generator.floor_plan_height,
                show=False,
                title=f"Floor plan (DB template) run {run_index}",
            )

        results.append(polygons)

    return results


def run_usable(
    vertices: list[tuple[float, float]] | None = None,
    offsets: list[float] | None = None,
    show: bool = True,
) -> list[tuple[float, float]]:
    """Return a usable buildable polygon and plot if requested.

    Defaults to a 10x5 rectangle with unit offsets when inputs are None.
    """
    finder = UsableSpaceFinder()

    if vertices is None or offsets is None:
        vertices = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]
        offsets = [1.0, 1.0, 1.0, 1.0]

    result = finder.find_buildable_space(vertices, offsets)

    if show:
        plotter = PolygonPlotter(output_base_dir="./app/dev/outputs")
        plotter.plot_boundary([vertices, result], show=True, title="Usable polygon")

    return result


def run_boundary(
    polygon: list[tuple[float, float]] | None = None,
    min_width: float = 1,
    min_height: float = 1,
    show: bool = True,
) -> tuple[list[tuple[float, float]] | None, list[tuple[float, float]] | None]:
    """Find boundary rectangles for a polygon and optionally plot results.

    Returns (parallel_rect, perpendicular_rect); either may be None.
    """
    bf = FPBoundaryFinder()
    if polygon is None:
        polygon = [(0, 0), (10, 0), (10, 5), (0, 5)]

    final_poly, rect_par, rect_perp = bf.fp_boundary_finder(
        polygon, min_width=min_width, min_height=min_height
    )

    if show:
        plotter = PolygonPlotter(output_base_dir="./app/dev/outputs")
        plotter.plot_boundary(
            [polygon, rect_par, rect_perp],
            show=True,
            title="Boundary rectangles",
        )

    return rect_par, rect_perp


def run_mocks():
    """Process each entry in MOCK_LANDS, generating and plotting examples."""
    # UsableSpaceFinder isn't needed here since run_usable handles it
    plotter = PolygonPlotter(output_base_dir="./app/dev/outputs")

    for idx, info in enumerate(MOCK_LANDS, start=1):
        verts = info["land_coordinates"]
        offsets = info["setbacksValues"]
        usable = run_usable(verts, offsets, show=False)
        rect_par, rect_perp = run_boundary(verts, show=False)
        floor_polys = run_floor(show=False)
        # plot everything in one set
        to_plot = [verts]
        if usable:
            to_plot.append(usable)
        if rect_par:
            to_plot.append(rect_par)
        if rect_perp:
            to_plot.append(rect_perp)
        to_plot.extend(floor_polys)
        plotter.polygon_line_plotter_single(
            to_plot,
            show=False,
            title=f"Mock {idx} full",
        )


def full_algorithm():
    """Execute the full pipeline (usable, boundary, floor) for all MOCK_LANDS.

    Returns a list of dictionaries containing the results for each entry.
    """
    all_results = []

    for idx, info in enumerate(MOCK_LANDS, start=1):
        land = info["land_coordinates"]
        offsets = info["setbacksValues"]
        usable = run_usable(land, offsets, show=False)
        rect_par, rect_perp = run_boundary(land, show=False)
        floor_polys = run_floor(show=False)

        result = {
            "land": land,
            "usable": usable,
            "boundary_parallel": rect_par,
            "boundary_perpendicular": rect_perp,
            "floor_polygons": floor_polys,
        }
        all_results.append(result)

        # combined = []
        # combined.append(land)
        # combined.append(usable)
        # # combined.append(rect_perp)
        # combined.append(floor_polys)
        # plotter.polygon_line_plotter_single(
        #     combined,
        #     show=False,
        #     title=f"Full run {idx}",
        # )

    return all_results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    command = sys.argv[1].lower()
    if command == "floor":
        # optional repeat count after the command
        count = 1
        if len(sys.argv) >= 3:
            try:
                count = max(1, int(sys.argv[2]))
            except ValueError:
                print(f"ignored invalid count '{sys.argv[2]}', using 1")
        run_floor(times=count)
    elif command == "usable":
        run_usable()
    elif command == "boundary":
        run_boundary()
    elif command == "mocks":
        run_mocks()
    elif command == "full":
        full_algorithm()
    else:
        pass
