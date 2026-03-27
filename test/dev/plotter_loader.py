from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Callable


def _load_plotter_from_path() -> Callable | None:
    base_dir = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) > 2 else Path(__file__).resolve().parents[-1]
    plotter_path = base_dir / "test" / "dev" / "api_result_plotter.py"
    if not plotter_path.exists():
        return None

    try:
        spec = spec_from_file_location("api_result_plotter", plotter_path)
        if not spec or not spec.loader:
            return None
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "plot_floor_plan_payload", None)
    except Exception:
        return None


plot_floor_plan_payload = _load_plotter_from_path()