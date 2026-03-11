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
from typing import Any, Dict, List, Tuple

from app.services.algorithm_manager import run_fpg
from app.util.layout_coordinates_clean_up import validate_layout

# reuse the dev plotting helper; import lazily in case matplotlib isn't
# installed in a production environment (debug module is dev-only anyway)
from app.algorithms.fp_formatter_for_frontend.dev_test.fpfff_plot_wall import (
    plot_points,
)

Point = Tuple[float, float]


# internal helpers --------------------------------------------------------

def _plot_raw_polygons(polygons: List[List[Point]]) -> None:
    """Scatter every vertex from *polygons*.

    The image is always written to ``raw_polygons.png`` under the module's
    ``images/`` directory.  Silent when the polygon list is empty.
    """
    if not polygons:
        print("run_fpg returned no polygons")
        return

    pts: List[Point] = []
    for poly in polygons:
        for p in poly:
            pts.append((float(p[0]), float(p[1])))
    # scatter plot for quick debugging
    plot_points(sorted(set(pts)), filename="raw_polygons.png")

    # additionally use PolygonPlotter (same class used by d-main) to create a
    # cleaned polygon drawing.  This mirrors the usage in d-main but points at
    # our local images directory so the output is easy to find.
    try:
        from app.dev.plotters import PolygonPlotter

        pp = PolygonPlotter(output_base_dir=os.path.join(
            os.path.dirname(__file__), "dev_test", "images"
        ))
        # polygon_line_plotter_single expects a list of polygon sets; we
        # supply the entire list as one set so each room polygon is drawn.
        pp.polygon_line_plotter_single(polygons, show=False, title="Raw polygons")
    except ImportError:
        # plotting is optional; absence of dev.plotters is non-fatal
        print("PolygonPlotter unavailable; skipped additional floor-plan plot")


def _plot_report_points(report: Any, filename: str) -> None:
    """Extract and plot coordinates appearing anywhere in *report*.

    Writes the scatter to *filename* within the module's ``images/``
    directory.  If no points are found a message is printed and nothing is
    saved.
    """
    pts: List[Point] = []
    _collect_points(report, pts)
    if not pts:
        print("no points extracted from report")
        return
    plot_points(sorted(set(pts)), filename=filename)



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

    # plot raw polygon vertices and then report-derived coordinates
    _plot_raw_polygons(polygons)
    report = validate_layout(polygons, generator)
    _plot_report_points(report, filename)
    return report


if __name__ == "__main__":
    # quick manual execution
    rep = debug_report_plot()
    print("report keys:", list(rep.keys()))
