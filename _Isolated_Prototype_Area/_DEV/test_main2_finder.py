"""Tests for usable_space_in_land-finder/main2.py (OOP wrapper)

Run manually: python _DEV/test_main2_finder.py
Or with pytest: pytest _DEV/test_main2_finder.py -q

The test uses importlib to load the module from its file path because the
package directory contains a hyphen and isn't a normal importable package
name. The test preserves output by default so you can inspect generated PNGs.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, cast

# (No static-only matplotlib import here — test injects a runtime stub when needed)

# Project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Preserve test output by default for manual inspection (one-time developer run)
KEEP_TEST_OUTPUT = True

MODULE_PATH = ROOT / "usable_space_in_land-finder" / "main2.py"


def _load_module_from_path(path: Path):
    """Load module from path. If matplotlib is not installed, inject a lightweight
    stub so import-time plotting modules succeed and saved-file calls create
    placeholder files for tests.
    """
    # Inject matplotlib stub when missing or broken so imports don't fail on CI/dev machines
    try:
        mpl_spec = importlib.util.find_spec("matplotlib")
    except Exception:
        mpl_spec = None
    if mpl_spec is None:
        import types

        if "matplotlib" not in sys.modules:
            mpl = types.ModuleType("matplotlib")
            mpl.__path__ = []

            # minimal 'ticker' submodule
            ticker = types.ModuleType("matplotlib.ticker")

            class MultipleLocator:
                def __init__(self, v):
                    self._v = v

            # Use setattr + cast to avoid static-analysis attribute-access errors
            setattr(cast(Any, ticker), "MultipleLocator", MultipleLocator)  # type: ignore[reportAttributeAccessIssue]
            sys.modules["matplotlib.ticker"] = ticker

            # minimal Figure / Axes classes
            fig_mod = types.ModuleType("matplotlib.figure")

            class Figure:
                pass

            # assign via setattr to avoid Pylance attribute-access warnings
            setattr(cast(Any, fig_mod), "Figure", Figure)  # type: ignore[reportAttributeAccessIssue]
            sys.modules["matplotlib.figure"] = fig_mod

            axes_mod = types.ModuleType("matplotlib.axes")

            class Axes:
                pass

            setattr(cast(Any, axes_mod), "Axes", Axes)  # type: ignore[reportAttributeAccessIssue]
            sys.modules["matplotlib.axes"] = axes_mod

            # minimal pyplot with save/show behaviors
            pyplot = types.ModuleType("matplotlib.pyplot")

            def subplots(figsize=(8, 8)):
                class FakeFig:
                    def __init__(self):
                        self._closed = False

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

                    def set_title(self, *a, **k):
                        pass

                    def set_xlabel(self, *a, **k):
                        pass

                    def set_ylabel(self, *a, **k):
                        pass

                    def set_aspect(self, *a, **k):
                        pass

                    def plot(self, *a, **k):
                        pass

                    def scatter(self, *a, **k):
                        pass

                    def text(self, *a, **k):
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

            def show():
                return None

            def close(fig):
                return None

            def tight_layout(*a, **k):
                return None

            def savefig(path, **kwargs):
                # create parent dir if needed and write a small placeholder file
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "wb") as f:
                        # write a minimal valid 1x1 PNG so image viewers can open test artifacts
                        f.write(
                            b"\x89PNG\r\n\x1a\n"
                            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                            b"\x00\x00\x00\nIDATx\x9cc\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
                        )
                except Exception:
                    pass

            # assign attributes via setattr + cast and add targeted ignores for Pylance
            setattr(cast(Any, pyplot), "subplots", subplots)  # type: ignore[reportAttributeAccessIssue]
            setattr(cast(Any, pyplot), "show", show)  # type: ignore[reportAttributeAccessIssue]
            setattr(cast(Any, pyplot), "close", close)  # type: ignore[reportAttributeAccessIssue]
            setattr(cast(Any, pyplot), "savefig", savefig)  # type: ignore[reportAttributeAccessIssue]
            setattr(cast(Any, pyplot), "tight_layout", tight_layout)  # type: ignore[reportAttributeAccessIssue]
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

            sys.modules["matplotlib"] = mpl
            sys.modules["matplotlib.pyplot"] = pyplot

    spec = importlib.util.spec_from_file_location("usable_space_main2", str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    # spec is narrowed to ModuleSpec so static checkers won't complain
    assert module is not None
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


def _cleanup(path: str):
    if KEEP_TEST_OUTPUT:
        return
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except Exception:
        pass


def test_compute_buildable_vertices_basic():
    module = _load_module_from_path(MODULE_PATH)
    Finder = getattr(module, "LandBuildableFinder")

    verts = [(4.0, 4.0), (2.0, 0.0), (10.0, 0.0), (10.0, 5.0)]
    offsets = [0.5, 0.8, 0.5, 10.0]

    finder = Finder(verts, offsets)
    buildable = finder.compute()

    assert isinstance(buildable, list)
    assert len(buildable) >= 3
    assert all(isinstance(p, tuple) and len(p) == 2 for p in buildable)
    assert all(isinstance(coord, float) for p in buildable for coord in p)


def test_plot_save_and_filename_pattern():
    module = _load_module_from_path(MODULE_PATH)
    Finder = getattr(module, "LandBuildableFinder")

    out_base = Path(__file__).parent / "test_output_main2"
    _cleanup(str(out_base))
    out_base.mkdir(parents=True, exist_ok=True)

    verts = [(4.0, 4.0), (2.0, 0.0), (10.0, 0.0), (10.0, 5.0)]
    offsets = [0.5, 0.8, 0.5, 10.0]

    finder = Finder(verts, offsets, output_base_dir=str(out_base))
    saved = finder.plot(show=False, save=True, batch_no=5, title="test-main2")

    assert saved and isinstance(saved, list) and len(saved) >= 1

    # Ensure files exist and non-empty
    for p in saved:
        assert os.path.exists(p)
        assert os.path.getsize(p) > 0

    # Filename pattern: YYYYMMDD-HHMMSSmmm_05_XXX.png
    pattern = re.compile(r"^\d{8}-\d{6}\d{3}_05_\d{3}\.png$")
    for p in saved:
        name = os.path.basename(p)
        assert pattern.match(name), f"Filename does not match pattern: {name}"

    if KEEP_TEST_OUTPUT:
        print("Preserved test output at:", out_base)

    _cleanup(str(out_base))


def run_all():
    print("Running _DEV/test_main2_finder.py")
    test_compute_buildable_vertices_basic()
    print(" - compute: PASS")
    test_plot_save_and_filename_pattern()
    print(" - plot+save: PASS")
    print("All tests passed")


if __name__ == "__main__":
    run_all()
