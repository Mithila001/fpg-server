"""engine.py – superseded.

The nav-mesh and A* logic now lives in:
  path_simulations/nav_mesh.py
  path_simulations/pathfinder.py

This stub is kept so any external references don't break at import time.
"""
# Re-export primary classes for backward compatibility
from ..nav_mesh import build_nav_mesh  # noqa: F401
from ..pathfinder import AStarGrid as PathSimulationEngine  # noqa: F401