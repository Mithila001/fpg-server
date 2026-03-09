# ruff: noqa: E402  # path manipulation occurs before imports below
from collections.abc import Sequence
import os
import sys

# python app/dev/d-main.py full

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


def run_floor(
    width: float = FLOOR_WIDTH,
    height: float = FLOOR_HEIGHT,
    rooms_data: list[RoomData] | None = None,
    show: bool = True,
) -> list[list[tuple[float, float]]]:
    """Create a floor plan and optionally plot it.

    Args:
        width: floor plan width
        height: floor plan height
        rooms_data: room specs as RoomData objects; if ``None`` the hardcoded
                    defaults below are used (sourced from RoomSizeConstraintBase)
        show: whether to display/save the resulting polygon (via ``PolygonPlotter``)

    Returns:
        A list of polygons (one per room) representing the solution.  If no
        solution was found the returned list will be empty.
    """
    print("running floor plan generator")

    # static defaults used when no explicit rooms_data is provided
    default_rooms: list[RoomData] = [
        RoomData("livingRoom1", "livingRoom", min_w=0, min_h=0, max_w=100, max_h=100),
        RoomData("bedroom1", "bedroom", min_w=0, min_h=0, max_w=100, max_h=100),
        RoomData("bathroom1", "bathroom", min_w=0, min_h=0, max_w=100, max_h=100),
        RoomData("kitchen1", "kitchen", min_w=0, min_h=0, max_w=100, max_h=100),
    ]

    config_obj = ConfigData(
        min_coverage=MIN_COVERAGE,
        max_aspect_ratio=16.0,
        min_aspect_ratio=0.0,
        floor_plan_width=width,
        floor_plan_height=height,
    )
    print("--- Requirements:", config_obj)
    requirements = FpgRequirements(
        rooms=rooms_data if rooms_data is not None else default_rooms,
        config=config_obj,
    )
    generator = FloorPlanGenerator(requirements)
    solved = generator.generate()
    if not solved:
        return []

    solution = generator.get_solution()

    for entry in solution:
        # room entries include name/type information
        print(f"  room: {entry.get('name')} size=({entry.get('w')}, {entry.get('h')})")

    # convert each room dict into a polygon of its bounding rectangle
    polygons: list[list[tuple[float, float]]] = []
    for r in solution:
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        polygons.append([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])

    plotter = PolygonPlotter(output_base_dir="./app/dev/outputs")
    plotter.floor_plan_plot(
        rooms_list=generator.rooms,
        solver=generator.solver,
        LAND_WIDTH=width,
        LAND_HEIGHT=height,
        show=show,
        title="Floor plan",
    )

    return polygons


def run_usable(
    vertices: list[tuple[float, float]] | None = None,
    offsets: list[float] | None = None,
    show: bool = True,
) -> list[tuple[float, float]]:
    """Compute a usable polygon, optionally plotting the result.

    If ``vertices`` or ``offsets`` are omitted, a simple square example is used.

    Returns the computed usable polygon (empty if computation fails).
    """
    print("running usable-land-space example")
    finder = UsableSpaceFinder()

    if vertices is None or offsets is None:
        vertices = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]
        offsets = [1.0, 1.0, 1.0, 1.0]

    result = finder.find_buildable_space(vertices, offsets)
    print("buildable polygon", result)

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
    """Compute boundary rectangles for a polygon and optionally plot them.

    Args:
        polygon: list of (x,y) vertices; defaults to a simple rectangle
        min_width: minimum candidate width for rectangles
        min_height: minimum candidate height
        show: whether to display/save the result

    Returns:
        Tuple of (parallel_rect, perpendicular_rect), each may be ``None`` if no
        valid rectangle was found.
    """
    print("running boundary finder example")
    bf = FPBoundaryFinder()
    if polygon is None:
        polygon = [(0, 0), (10, 0), (10, 5), (0, 5)]

    final_poly, rect_par, rect_perp = bf.fp_boundary_finder(
        polygon, min_width=min_width, min_height=min_height
    )
    print("rectangles", rect_par, rect_perp)

    if show:
        plotter = PolygonPlotter(output_base_dir="./app/dev/outputs")
        plotter.plot_boundary(
            [polygon, rect_par, rect_perp],
            show=True,
            title="Boundary rectangles",
        )

    return rect_par, rect_perp


def run_mocks():
    """Iterate over ``MOCK_LANDS`` and produce usable polygons + plots.

    Each terrain is processed by :class:`UsableSpaceFinder` and the original
    land polygon is drawn alongside the computed buildable polygon.  Images
    are saved in the same output directory used by the other examples.
    """
    print("running mock-land batch")
    # UsableSpaceFinder isn't needed here since run_usable handles it
    plotter = PolygonPlotter(output_base_dir="./app/dev/outputs")

    for idx, info in enumerate(MOCK_LANDS, start=1):
        verts = info["land_coordinates"]
        offsets = info["setbacksValues"]
        usable = run_usable(verts, offsets, show=False)
        rect_par, rect_perp = run_boundary(verts, show=False)
        floor_polys = run_floor(show=False)
        print(
            f"mock {idx}: land={verts}, usable={usable}, boundary={rect_par},{rect_perp}, floor_rooms={len(floor_polys)}"
        )
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
    """Run the entire pipeline against every entry in ``MOCK_LANDS``.

    For each parcel the steps are:
    1. compute usable polygon
    2. compute boundary rectangles
    3. generate a floor plan (default config)
    4. collect results and save a combined plot

    The function returns a list of result dictionaries for further processing
    if desired.
    """
    print("executing full algorithm on all mock lands")
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
        print("usage: python d-main.py <floor|usable|boundary|mocks|full>")
        sys.exit(1)
    command = sys.argv[1].lower()
    if command == "floor":
        run_floor()
    elif command == "usable":
        run_usable()
    elif command == "boundary":
        run_boundary()
    elif command == "mocks":
        run_mocks()
    elif command == "full":
        full_algorithm()
    else:
        print("unknown command", command)
