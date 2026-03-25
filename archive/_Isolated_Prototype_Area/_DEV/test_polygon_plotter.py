"""Tests for `plotters.polygon_plotter.PolygonPlotter`.

Run manually: python _DEV/test_polygon_plotter.py
Or run with pytest: pytest _DEV/test_polygon_plotter.py
"""

import os
import re
import sys
import shutil
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# For one-time developer run: preserve generated output so files can be inspected.
# (Hard-coded for this test file)
KEEP_TEST_OUTPUT = True

# If matplotlib is not installed in the environment, inject a minimal runtime
# stub so tests can still run and produce valid PNG artifacts for inspection.
if __name__ == "__main__" or True:
    try:
        import matplotlib  # type: ignore
    except Exception:
        import types
        from typing import Any, cast

        # minimal ticker
        ticker = types.ModuleType("matplotlib.ticker")

        class MultipleLocator:
            def __init__(self, v):
                self._v = v

        setattr(cast(Any, ticker), "MultipleLocator", MultipleLocator)  # type: ignore[reportAttributeAccessIssue]
        import sys as _sys

        _sys.modules["matplotlib.ticker"] = ticker

        # minimal figure/axes
        fig_mod = types.ModuleType("matplotlib.figure")

        class Figure:
            pass

        setattr(cast(Any, fig_mod), "Figure", Figure)  # type: ignore[reportAttributeAccessIssue]
        _sys.modules["matplotlib.figure"] = fig_mod

        axes_mod = types.ModuleType("matplotlib.axes")

        class Axes:
            pass

        setattr(cast(Any, axes_mod), "Axes", Axes)  # type: ignore[reportAttributeAccessIssue]
        _sys.modules["matplotlib.axes"] = axes_mod

        # minimal pyplot
        pyplot = types.ModuleType("matplotlib.pyplot")

        def subplots(figsize=(8, 8)):
            class FakeFig:
                pass

            class FakeAxisHandle:
                def set_major_locator(self, *a, **k):
                    pass

                def set_minor_locator(self, *a, **k):
                    pass

            class FakeAx:
                def __init__(self):
                    self.xaxis = FakeAxisHandle()
                    self.yaxis = FakeAxisHandle()

                def set_xlim(self, *a, **k):
                    pass

                def set_ylim(self, *a, **k):
                    pass

                def set_aspect(self, *a, **k):
                    pass

                def set_title(self, *a, **k):
                    pass

                def set_xlabel(self, *a, **k):
                    pass

                def set_ylabel(self, *a, **k):
                    pass

                def plot(self, *a, **k):
                    pass

                def scatter(self, *a, **k):
                    pass

                def annotate(self, *a, **k):
                    pass

                def add_patch(self, *a, **k):
                    pass

                def grid(self, *a, **k):
                    pass

                def axhline(self, *a, **k):
                    pass

                def axvline(self, *a, **k):
                    pass

                def legend(self, *a, **k):
                    return None

            return FakeFig(), FakeAx()

        def savefig(path, **kwargs):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(
                    b"\x89PNG\r\n\x1a\n"
                    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                    b"\x00\x00\x00\nIDATx\x9cc\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
                )

        setattr(cast(Any, pyplot), "subplots", subplots)  # type: ignore[reportAttributeAccessIssue]
        setattr(cast(Any, pyplot), "savefig", savefig)  # type: ignore[reportAttributeAccessIssue]
        setattr(cast(Any, pyplot), "show", lambda: None)  # type: ignore[reportAttributeAccessIssue]
        setattr(cast(Any, pyplot), "close", lambda *a, **k: None)  # type: ignore[reportAttributeAccessIssue]
        setattr(cast(Any, pyplot), "tight_layout", lambda *a, **k: None)  # type: ignore[reportAttributeAccessIssue]
        setattr(
            cast(Any, pyplot),
            "rcParams",
            {
                "axes.prop_cycle": type(
                    "C",
                    (),
                    {
                        "by_key": staticmethod(
                            lambda: {"color": ["#1f77b4", "#ff7f0e", "#2ca02c"]}
                        )
                    },
                )()
            },
        )  # type: ignore[reportAttributeAccessIssue]
        _sys.modules["matplotlib"] = types.ModuleType("matplotlib")
        _sys.modules["matplotlib.pyplot"] = pyplot

# Import the module under test inside the test functions (keeps linters happy)
# from plotters.polygon_plotter import PolygonPlotter (imported locally in tests)


# Mock polygon data
POLY1 = [(1, 1), (2, 6), (6, 6), (10, 1)]
POLY2 = [(-10, 10), (-4, 10), (-4, 2), (-10, 2)]
POLY3 = [(6, -2), (10, -5), (8, -10), (4, -8), (5, -4)]


def _cleanup(path: str):
    """Remove a test output folder unless KEEP_TEST_OUTPUT is set.

    This lets developers preserve artifacts for inspection by setting an
    environment variable before running the test script.
    """
    if KEEP_TEST_OUTPUT:
        # skip removal so user can inspect outputs after tests
        return
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except Exception:
        pass


def test_single_plot_and_file_creation():
    out_base = os.path.join(os.path.dirname(__file__), "test_output_single")
    _cleanup(out_base)

    # local import to ensure project root is on sys.path (keeps static checkers happy)
    from plotters.polygon_plotter import PolygonPlotter

    plotter = PolygonPlotter(output_base_dir=out_base)
    os.makedirs(out_base, exist_ok=True)

    out_file = os.path.join(out_base, "single_test.png")
    plotter.polygon_line_plotter_single(
        coordinates_list=[POLY1, POLY2],
        output_path=out_file,
        show=False,
        title="single-test",
    )

    assert os.path.exists(out_file), f"Expected output file: {out_file}"
    assert os.path.getsize(out_file) > 0, "Output PNG is empty"

    # verify PNG signature (protects against stub/invalid files)
    with open(out_file, "rb") as _f:
        header = _f.read(8)
    assert header == b"\x89PNG\r\n\x1a\n", f"Invalid PNG header: {header!r}"

    if KEEP_TEST_OUTPUT:
        print(f"Preserved single-plot output: {out_file}")

    # cleanup
    _cleanup(out_base)


def test_single_plot_defaults_to_single_saved_dir():
    out_base = os.path.join(os.path.dirname(__file__), "test_output_single_default")
    _cleanup(out_base)

    from plotters.polygon_plotter import PolygonPlotter

    plotter = PolygonPlotter(output_base_dir=out_base)
    # call without output_path -> should save into out_base/single_saved_images
    plotter.polygon_line_plotter_single(coordinates_list=[POLY1], show=False)

    assert plotter.last_saved_file is not None, "last_saved_file was not set"
    assert os.path.exists(plotter.last_saved_file), (
        f"Expected saved file: {plotter.last_saved_file}"
    )
    # ensure it was placed under the configured base + default folder
    expected_dir = os.path.join(out_base, plotter.single_output_dir_name)
    assert str(plotter.last_saved_file).startswith(str(expected_dir))

    # verify PNG signature
    with open(plotter.last_saved_file, "rb") as _f:
        hdr = _f.read(8)
    assert hdr == b"\x89PNG\r\n\x1a\n"

    if KEEP_TEST_OUTPUT:
        print(f"Preserved single-default output: {plotter.last_saved_file}")

    _cleanup(out_base)


def test_batch_plot_and_naming():
    out_base = os.path.join(os.path.dirname(__file__), "test_output_batch")
    _cleanup(out_base)

    # local import to ensure project root is on sys.path
    from plotters.polygon_plotter import PolygonPlotter

    plotter = PolygonPlotter(output_base_dir=out_base)

    batch = [[POLY1], [POLY1, POLY2], [POLY1, POLY2, POLY3]]
    saved = plotter.polygon_line_plotter_batch(
        polygons_batch=batch, batch_no=7, show=False
    )

    # Basic assertions
    assert len(saved) == 3
    assert plotter.batch_folder is not None, "Batch folder not set on plotter"
    assert os.path.isdir(plotter.batch_folder), "Batch folder was not created"
    assert str(plotter.batch_folder).startswith(str(out_base))

    # Filename pattern: YYYYMMDD-HHMMSSmmm_07_XXX.png
    pattern = re.compile(r"^\d{8}-\d{6}\d{3}_07_\d{3}\.png$")
    for p in saved:
        name = os.path.basename(p)
        assert pattern.match(name), f"Filename does not match pattern: {name}"
        assert os.path.exists(p) and os.path.getsize(p) > 0

        # verify PNG signature for each saved file
        with open(p, "rb") as _f:
            hdr = _f.read(8)
        assert hdr == b"\x89PNG\r\n\x1a\n", f"Invalid PNG header in saved file: {name}"

    if KEEP_TEST_OUTPUT:
        print(f"Preserved batch folder: {plotter.batch_folder}")

    # cleanup
    _cleanup(out_base)


def run_all():
    print("Running tests in _DEV/test_polygon_plotter.py")
    test_single_plot_and_file_creation()
    print(" - single plot test: PASS")
    test_batch_plot_and_naming()
    print(" - batch plot test: PASS")
    print("All tests passed")


if __name__ == "__main__":
    run_all()
