"""A* pathfinder on a rasterized navigation mesh.

Handles:
  - Rasterization of a Shapely nav-mesh into a binary grid (0=walkable, 1=obstacle)
  - Room-type labeling per cell (for scoring)
  - A* with octile heuristic and 8-directional movement
  - Chaikin corner-cutting for smooth, human-like paths
  - Traffic accumulation map

No imports from outside this package.
"""

from __future__ import annotations

import heapq
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Use dev_print for debugging as requested
from ._dev_print import dev_print
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

# Room type integer codes (stored in room_type_grid)
ROOM_TYPE_CODES: Dict[str, int] = {
    "livingRoom": 1,
    "bedroom": 2,
    "kitchen": 3,
    "bathroom": 4,
    "attachedBathroom": 4,
    "hallway": 5,
    "diningRoom": 6,
    "garage": 7,
    "verandaOutdoorSpace": 8,
}
OBSTACLE_CODE = 0
OTHER_CODE = 9

_GridIdx = Tuple[int, int]  # (row, col) = (iy, ix)
_WorldPt = Tuple[float, float]  # (x, y) in cm


class AStarGrid:
    """Rasterized nav-mesh with A* pathfinding and traffic tracking."""

    def __init__(self, resolution: float = 15.0) -> None:
        self.resolution = resolution
        self._min_x: float = 0.0
        self._min_y: float = 0.0
        self._height: int = 0
        self._width: int = 0

        # Core grids – allocated after rasterize()
        self.walkable: Optional[np.ndarray] = None  # bool (True = walkable)
        self.traffic_map: Optional[np.ndarray] = None  # float64 hit counts
        self.room_type_grid: Optional[np.ndarray] = None  # int8 room type codes

        dev_print("path", f"Initialized AStarGrid with resolution: {resolution}")

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    # ------------------------------------------------------------------
    # Rasterisation
    # ------------------------------------------------------------------

    def rasterize(self, nav_mesh: Any) -> None:
        """Build binary walkable grid from a Shapely geometry."""
        min_x, min_y, max_x, max_y = nav_mesh.bounds
        self._min_x = float(min_x)
        self._min_y = float(min_y)

        width = max(1, int((max_x - min_x) / self.resolution) + 1)
        height = max(1, int((max_y - min_y) / self.resolution) + 1)
        self._width = width
        self._height = height

        dev_print(
            "path",
            f"Rasterizing grid: {width}x{height} | Bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})",
        )

        self.walkable = np.zeros((height, width), dtype=bool)
        self.traffic_map = np.zeros((height, width), dtype=np.float64)
        self.room_type_grid = np.full((height, width), OTHER_CODE, dtype=np.int8)

        prepared = prep(nav_mesh)
        res = self.resolution
        ox, oy = self._min_x, self._min_y

        walkable_count = 0
        for iy in range(height):
            cy = oy + (iy + 0.5) * res
            for ix in range(width):
                cx = ox + (ix + 0.5) * res
                if prepared.contains(Point(cx, cy)):
                    self.walkable[iy, ix] = True  # type: ignore[index]
                    walkable_count += 1

        dev_print(
            "path",
            f"Rasterization complete. Walkable cells: {walkable_count}/{width * height}",
        )

    def label_room_types(self, rooms: List[Any]) -> None:
        """Assign each walkable cell a room-type code from the room that contains it."""
        if self.walkable is None or self.room_type_grid is None:
            dev_print("path", "label_room_types aborted: Grid not rasterized.")
            return

        res = self.resolution
        ox, oy = self._min_x, self._min_y

        # Build (prepared_poly, code) pairs – process all rooms
        prepared_rooms: List[Tuple[Any, int]] = []
        for room in rooms:
            verts = self._get(room, "vertices", None)
            if not verts or len(verts) < 3:
                continue
            poly = Polygon(verts)
            if poly.is_empty or not poly.is_valid:
                continue
            r_type = str(self._get(room, "type", ""))
            code = ROOM_TYPE_CODES.get(r_type, OTHER_CODE)
            prepared_rooms.append((prep(poly), code))

        dev_print("path", f"Labeling {len(prepared_rooms)} rooms onto grid.")

        for iy in range(self._height):
            if not np.any(self.walkable[iy]):  # type: ignore[index]
                continue
            cy = oy + (iy + 0.5) * res
            for ix in range(self._width):
                if not self.walkable[iy, ix]:  # type: ignore[index]
                    continue
                cx = ox + (ix + 0.5) * res
                pt = Point(cx, cy)
                for prep_poly, code in prepared_rooms:
                    if prep_poly.contains(pt):
                        self.room_type_grid[iy, ix] = code  # type: ignore[index]
                        break
        dev_print("path", "Room labeling complete.")

    # ------------------------------------------------------------------
    # Coordinate utilities
    # ------------------------------------------------------------------

    def _world_to_grid(self, pt: _WorldPt) -> _GridIdx:
        ix = int((pt[0] - self._min_x) / self.resolution)
        iy = int((pt[1] - self._min_y) / self.resolution)
        ix = max(0, min(self._width - 1, ix))
        iy = max(0, min(self._height - 1, iy))
        return (iy, ix)

    def _grid_to_world(self, idx: _GridIdx) -> _WorldPt:
        x = self._min_x + (idx[1] + 0.5) * self.resolution
        y = self._min_y + (idx[0] + 0.5) * self.resolution
        return (x, y)

    # ------------------------------------------------------------------
    # A* pathfinding
    # ------------------------------------------------------------------

    def find_path(self, start_pt: _WorldPt, end_pt: _WorldPt) -> List[_WorldPt]:
        """Return smoothed world-coordinate path from start to end."""
        if self.walkable is None or self.traffic_map is None:
            dev_print("path", "find_path failed: Grid not initialized.")
            return []

        start_grid = self._world_to_grid(start_pt)
        goal_grid = self._world_to_grid(end_pt)

        # Snap non-walkable endpoints to nearest walkable cell
        start = self._nearest_walkable(start_grid)
        goal = self._nearest_walkable(goal_grid)

        if start is None or goal is None:
            dev_print(
                "path",
                f"Path failed: Start {start_grid} or Goal {goal_grid} out of reach/blocked.",
            )
            return []

        if start != start_grid or goal != goal_grid:
            dev_print(
                "path", f"Snapped endpoints: {start_grid}->{start}, {goal_grid}->{goal}"
            )

        if start == goal:
            dev_print("path", "Start and Goal are the same cell.")
            return [self._grid_to_world(start)]

        raw_path = self._astar(start, goal)
        if not raw_path:
            dev_print("path", f"A* failed to find path between {start} and {goal}")
            return []

        dev_print("path", f"A* found raw path with {len(raw_path)} nodes.")

        # Smooth and update traffic
        smoothed = self.smooth_path(raw_path, iterations=3)
        self._mark_traffic(raw_path)  # mark on unsmoothed path for accuracy

        dev_print("path", f"Path smoothed. Final world point count: {len(smoothed)}")
        return smoothed

    def _nearest_walkable(
        self, idx: _GridIdx, max_radius: int = 8
    ) -> Optional[_GridIdx]:
        """Find nearest walkable cell to idx within max_radius cells."""
        if self.walkable is None:
            return None
        iy, ix = idx
        if self.walkable[iy, ix]:
            return idx
        for r in range(1, max_radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if abs(dy) != r and abs(dx) != r:
                        continue
                    ny, nx = iy + dy, ix + dx
                    if 0 <= ny < self._height and 0 <= nx < self._width:
                        if self.walkable[ny, nx]:
                            return (ny, nx)
        return None

    def _astar(self, start: _GridIdx, goal: _GridIdx) -> List[_GridIdx]:
        assert self.walkable is not None
        h, w = self._height, self._width

        def heuristic(a: _GridIdx, b: _GridIdx) -> float:
            dx = abs(a[1] - b[1])
            dy = abs(a[0] - b[0])
            return (dx + dy) + (1.414 - 2.0) * min(dx, dy)  # octile

        queue: List[Tuple[float, _GridIdx]] = [(0.0, start)]
        came_from: Dict[_GridIdx, _GridIdx] = {}
        g_score: Dict[_GridIdx, float] = {start: 0.0}

        nodes_explored = 0
        while queue:
            _, current = heapq.heappop(queue)
            nodes_explored += 1

            if current == goal:
                path: List[_GridIdx] = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            for dy, dx in [
                (0, 1),
                (0, -1),
                (1, 0),
                (-1, 0),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ]:
                ny, nx = current[0] + dy, current[1] + dx
                nb: _GridIdx = (ny, nx)
                if not (0 <= ny < h and 0 <= nx < w):
                    continue
                if not self.walkable[ny, nx]:
                    continue

                move_cost = 1.414 if (abs(dy) + abs(dx) == 2) else 1.0
                tentative_g = g_score[current] + move_cost
                if tentative_g < g_score.get(nb, float("inf")):
                    came_from[nb] = current
                    g_score[nb] = tentative_g
                    f = tentative_g + heuristic(nb, goal)
                    heapq.heappush(queue, (f, nb))

        dev_print(
            "path", f"A* Search exhausted after exploring {nodes_explored} nodes."
        )
        return []

    def _mark_traffic(self, path: List[_GridIdx]) -> None:
        assert self.traffic_map is not None
        for idx in path:
            self.traffic_map[idx] += 1.0  # type: ignore[index]

    # ------------------------------------------------------------------
    # Chaikin smoothing
    # ------------------------------------------------------------------

    def smooth_path(
        self,
        path: List[_GridIdx],
        iterations: int = 3,
    ) -> List[_WorldPt]:
        """Convert grid indices → world coords and apply Chaikin smoothing."""
        if not path:
            return []
        world: List[_WorldPt] = [self._grid_to_world(idx) for idx in path]
        if len(world) < 3:
            return world

        pts = world
        for j in range(iterations):
            new_pts: List[_WorldPt] = [pts[0]]
            for i in range(len(pts) - 1):
                x0, y0 = pts[i]
                x1, y1 = pts[i + 1]
                new_pts.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
                new_pts.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
            new_pts.append(pts[-1])
            pts = new_pts

        return pts

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """(min_x, min_y, max_x, max_y) of the rasterized area."""
        max_x = self._min_x + self._width * self.resolution
        max_y = self._min_y + self._height * self.resolution
        return (self._min_x, self._min_y, max_x, max_y)
