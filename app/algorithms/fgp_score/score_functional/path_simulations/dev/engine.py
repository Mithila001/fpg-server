import numpy as np
import heapq
import os
from typing import List, Tuple, Dict, Any, Optional, Union, cast
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

class PathSimulationEngine:
    def __init__(self, resolution: float = 0.2):
        self.resolution: float = resolution
        # Use Optional and explicit types to satisfy Pylance
        self.grid: Optional[np.ndarray] = None 
        self.meta: Dict[str, float] = {} 
        self.traffic_map: Optional[np.ndarray] = None

    def create_nav_mesh(self, floor_poly: Polygon, walls: List[Polygon], doors: List[Polygon]) -> Union[Polygon, MultiPolygon]:
        """Subtracts walls from floor. Returns Polygon or MultiPolygon."""
        wall_union = unary_union(walls)
        door_union = unary_union(doors)
        # Type cast because difference returns BaseGeometry
        effective_obstacles = wall_union.difference(door_union)
        nav_mesh = floor_poly.difference(effective_obstacles)
        
        if not isinstance(nav_mesh, (Polygon, MultiPolygon)):
            raise ValueError("Navigation mesh calculation did not result in a valid area.")
        return nav_mesh

    def rasterize(self, nav_mesh: Union[Polygon, MultiPolygon]) -> None:
        min_x, min_y, max_x, max_y = nav_mesh.bounds
        width = int((max_x - min_x) / self.resolution) + 1
        height = int((max_y - min_y) / self.resolution) + 1
        
        # Initialize with explicit dtypes
        self.grid = np.ones((height, width), dtype=np.int32) 
        self.meta = {'min_x': min_x, 'min_y': min_y, 'res': self.resolution}
        self.traffic_map = np.zeros((height, width), dtype=np.float64)
        
        for iy in range(height):
            y = min_y + (iy + 0.5) * self.resolution
            for ix in range(width):
                x = min_x + (ix + 0.5) * self.resolution
                if nav_mesh.contains(Point(x, y)):
                    self.grid[iy, ix] = 0

    def world_to_grid(self, pt: Tuple[float, float]) -> Tuple[int, int]:
        ix = int((pt[0] - self.meta['min_x']) / self.meta['res'])
        iy = int((pt[1] - self.meta['min_y']) / self.meta['res'])
        return (iy, ix)

    def grid_to_world(self, idx: Tuple[int, int]) -> Tuple[float, float]:
        x = self.meta['min_x'] + (idx[1] + 0.5) * self.meta['res']
        y = self.meta['min_y'] + (idx[0] + 0.5) * self.meta['res']
        return (x, y)

    def astar(self, start_pt: Tuple[float, float], end_pt: Tuple[float, float]) -> List[Tuple[float, float]]:
        if self.grid is None or self.traffic_map is None:
            return []

        start = self.world_to_grid(start_pt)
        goal = self.world_to_grid(end_pt)
        
        h, w = self.grid.shape
        if not (0 <= start[0] < h and 0 <= start[1] < w) or self.grid[start] == 1:
            return []

        # Ensure priority is float to match neighbor weights (1.414)
        queue: List[Tuple[float, Tuple[int, int]]] = [(0.0, start)]
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {start: 0.0}
        
        while queue:
            _, current = heapq.heappop(queue)
            if current == goal:
                path = []
                while current in came_from:
                    path.append(self.grid_to_world(current))
                    # traffic_map is float64, so float addition is fine
                    self.traffic_map[current] += 1.0 
                    current = came_from[current]
                return path[::-1]

            for dy, dx in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
                neighbor = (current[0] + dy, current[1] + dx)
                if 0 <= neighbor[0] < h and 0 <= neighbor[1] < w and self.grid[neighbor] == 0:
                    weight = 1.414 if abs(dy) + abs(dx) == 2 else 1.0
                    tentative_g = g_score[current] + weight
                    if tentative_g < g_score.get(neighbor, float('inf')):
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f = tentative_g + float(abs(neighbor[0]-goal[0]) + abs(neighbor[1]-goal[1]))
                        heapq.heappush(queue, (f, neighbor))
        return []

    def smooth_path(self, path: List[Tuple[float, float]], iterations: int = 2) -> List[Tuple[float, float]]:
        if len(path) < 3: return path
        current_path = path
        for _ in range(iterations):
            new_path = [current_path[0]]
            for i in range(len(current_path) - 1):
                p0 = np.array(current_path[i])
                p1 = np.array(current_path[i+1])
                q = 0.75 * p0 + 0.25 * p1
                r = 0.25 * p0 + 0.75 * p1
                new_path.append((float(q[0]), float(q[1])))
                new_path.append((float(r[0]), float(r[1])))
            new_path.append(current_path[-1])
            current_path = new_path
        return current_path