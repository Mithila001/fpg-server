"""Helpers for algorithm debugging.

This module provides a quick entry point that runs the floor planner,
validates the layout using the existing ``validate_layout`` helper, and then
visualises any coordinate pairs found in the resulting report.  The plotting
uses the same lightweight helper residing in ``dev_test/fpfff_plot_wall.py``;
no additional cleaning or transformation is performed so you can inspect the
raw diagnostic output directly.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime

from app.services.algorithm_manager import run_fpg, quicklyRunWithDbData
from app.util.layout_coordinates_clean_up import validate_layout

# formatter class needed by debug helper
from app.algorithms.fp_formatter_for_frontend.fp_wall_formatter import FpFormatter

# we reference the solver type in type hints; import to satisfy mypy
from app.algorithms.floor_plan_generator.generator import FloorPlanGenerator

# reuse the dev plotting helper; import lazily in case matplotlib isn't
# installed in a production environment (debug module is dev-only anyway)
from app.algorithms.fp_formatter_for_frontend.dev_test.fpfff_plot_wall import (
    plot_points, plot_segment_sets,
)

Point = Tuple[float, float]


# internal helpers --------------------------------------------------------


def _plot_raw_polygons(
    polygons: List[List[Point]], out_dir: str, file_name: str = "raw_polygons"
) -> None:
    """Scatter every vertex from *polygons*.

    The image is always written to ``raw_polygons.png`` within *out_dir*.
    Silent when the polygon list is empty.
    """
    if not polygons:
        print("run_fpg returned no polygons")
        return

    pts: List[Point] = []
    for poly in polygons:
        for p in poly:
            pts.append((float(p[0]), float(p[1])))
    # scatter plot for quick debugging
    plot_points(sorted(set(pts)), filename=os.path.join(out_dir, file_name))

    # additionally use PolygonPlotter (same class used by d-main) to create a
    # cleaned polygon drawing.  This mirrors the usage in d-main but points at
    # our chosen output directory so the output is easy to find.
    try:
        from app.dev.plotters import PolygonPlotter

        pp = PolygonPlotter(output_base_dir=out_dir)
        # polygon_line_plotter_single expects a list of polygon sets; we
        # supply the entire list as one set so each room polygon is drawn.
        pp.polygon_line_plotter_single(polygons, show=False, title="Raw polygons")
    except ImportError:
        # plotting is optional; absence of dev.plotters is non-fatal
        print("PolygonPlotter unavailable; skipped additional floor-plan plot")


def _plot_report_points(report: Any, filename: str, out_dir: str) -> None:
    """Extract and plot coordinates appearing anywhere in *report*.

    Writes the scatter to *filename* located inside *out_dir*.  If no points
    are found a message is printed and nothing is saved.
    """
    pts: List[Point] = []
    _collect_points(report, pts)
    if not pts:
        print("no points extracted from report")
        return
    plot_points(sorted(set(pts)), filename=os.path.join(out_dir, filename))


def _collect_points(obj: Any, acc: List[Point]) -> None:
    """Recursively gather 2‑tuples of numbers from *obj* into *acc*.

    This naïve walker descends into lists, tuples and dicts.  It treats any
    length‑2 sequence of ints or floats as a point.  The function is intended
    for the varied structure of the ``validate_layout`` report where
    coordinates may appear in lists, tuples or embedded in dictionaries.
    """
    if isinstance(obj, dict):
        for value in obj.values():
            _collect_points(value, acc)
        return

    if isinstance(obj, (list, tuple)):
        if len(obj) == 2 and all(isinstance(v, (int, float)) for v in obj):
            acc.append((float(obj[0]), float(obj[1])))
            return
        for item in obj:
            _collect_points(item, acc)


def debug_report_plot(filename: str = "debug_report_points.png") -> Dict[str, Any]:
    """Run the floor planner, validate layout, and plot report coordinates.

    The return value is the full report dictionary produced by
    :func:`app.util.layout_coordinates_clean_up.validate_layout`.  As a side
    effect a scatter plot containing every ``(x, y)`` pair found anywhere in
    the report is written into the ``images/`` directory next to this file.

    Args:
        filename: output PNG file name (placed in ``debug/``'s ``images`` dir).

    Returns:
        The validation report for programmatic inspection.
    """
    polygons, generator = run_fpg()

    # create timestamped output directory inside dev_test/images
    base_dir = os.path.join(os.path.dirname(__file__), "dev_test", "images")
    ts = datetime.now().strftime("%Y%m%d-%H-%M-%S")
    out_dir = os.path.join(base_dir, ts)
    os.makedirs(out_dir, exist_ok=True)

    # plot raw polygon vertices and then report-derived coordinates
    _plot_raw_polygons(polygons, out_dir, file_name="raw_polygons")
    report = validate_layout(polygons, generator)
    _plot_report_points(report, filename, out_dir)
    return report


def debug_fp_formatter() -> tuple[list[list[Point]], Optional["FloorPlanGenerator"]]:
    """Run the database-backed generator and pass layout to :class:`FpFormatter`.

    This helper mirrors the behaviour requested by the user: it invokes
    :func:`app.services.algorithm_manager.quicklyRunWithDbData` to obtain the
    resulting polygons and generator instance, then constructs an
    :class:`FpFormatter` and calls its :meth:`main` method using the polygons
    as the *room_layout* argument.  The return values from the generator are
    returned to the caller for any further inspection.
    """

    polygons, generator = quicklyRunWithDbData()
    fmt = FpFormatter()
    snapped = fmt.fpFormatter(polygons)

    # helper to flatten the dictionary-of-intervals into a list-of-lists
    def _flatten_intervals(data: Dict[float, List[Point]]) -> List[List[Point]]:
        """Return the values of *data* as a plain list-of-lists.

        The formatter routines produce the axis-aligned decomposition as a
        mapping from coordinate (float) to a list of intervals.  For
        quick inspectfion we often just want the inner lists; this helper
        drops the keys and returns them in insertion order.
        """
        return list(data.values())

    # # demonstrate conversion in the debug output
    # flat_horiz = _flatten_intervals(horiz)
    # flat_vert = _flatten_intervals(vert)

    # show the flattened results; this mirrors the example transformation the
    # user asked about in their message.


    # plot whatever the formatter returned so we can inspect it visually
    base_dir = os.path.join(os.path.dirname(__file__), "dev_test", "images")
    ts = datetime.now().strftime("%Y%m%d-%H-%M-%S")
    out_dir = os.path.join(base_dir, f"{ts}-formatted")
    os.makedirs(out_dir, exist_ok=True)
    
    # reuse the raw polygon plot helper; formatted data will usually be a list
    # of polygons but we treat it generically for now.
    _plot_raw_polygons(polygons, out_dir, file_name="raw_layout.png")
    # combine horizontal & vertical flattened sets for a single plot
    # plot_segment_sets(horiz_sets=flat_horiz, vert_sets=flat_vert,out_dir=out_dir, filename="combined_segments.png")

    return polygons, generator


if __name__ == "__main__":
    # allow easy invocation of helpers from the project root e.g.
    #   python3 -m app.algorithms.fp_formatter_for_frontend.debug formatter
    #   python app/algorithms/fp_formatter_for_frontend/debug.py report
    import sys

    if len(sys.argv) >= 2:
        cmd = sys.argv[1].lower()
        if cmd == "formatter":
            debug_fp_formatter()
        elif cmd == "report":
            rep = debug_report_plot()
            print("report keys:", list(rep.keys()))
        else:
            print(f"unknown command '{cmd}' (formatter|report)")
    else:
        # default behaviour remains the report helper
        rep = debug_report_plot()
        print("report keys:", list(rep.keys()))
