from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from os import makedirs
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


@dataclass
class _Grid:
    xs: List[float]
    ys: List[float]
    mask: List[List[bool]]
    cell_size: float
    origin: Tuple[float, float]


def _normalize_str(value: Any) -> str:
    return str(value or "").strip().lower()


def _opening_type(value: Any) -> str:
    normalized = _normalize_str(value)
    aliases = {
        "maindoor": "maindoor",
        "main_door": "maindoor",
        "backdoor": "backdoor",
        "back_door": "backdoor",
        "internaldoor": "internaldoor",
        "internal_door": "internaldoor",
        "window": "window",
    }
    return aliases.get(normalized, normalized)


def _room_center(room: Mapping[str, Any]) -> Tuple[float, float]:
    x = float(room.get("x", 0.0))
    y = float(room.get("y", 0.0))
    x_end = float(room.get("x_end", x))
    y_end = float(room.get("y_end", y))
    return (x + x_end) / 2.0, (y + y_end) / 2.0


def _door_midpoint(opening: Mapping[str, Any]) -> Tuple[float, float] | None:
    try:
        x1 = float(opening["x1"])
        y1 = float(opening["y1"])
        x2 = float(opening["x2"])
        y2 = float(opening["y2"])
    except (KeyError, TypeError, ValueError):
        return None
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def _build_room_index(rooms: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {
        _normalize_str(room.get("name")): room
        for room in rooms
        if _normalize_str(room.get("name"))
    }


def _room_polygons(rooms: Sequence[Mapping[str, Any]]):
    from shapely.geometry import Polygon

    polys = []
    by_type: Dict[str, List[Any]] = {}
    for room in rooms:
        try:
            x = float(room["x"])
            y = float(room["y"])
            x_end = float(room["x_end"])
            y_end = float(room["y_end"])
        except (KeyError, TypeError, ValueError):
            continue
        poly = Polygon([(x, y), (x_end, y), (x_end, y_end), (x, y_end)])
        if poly.is_empty:
            continue
        polys.append(poly)
        room_type = _normalize_str(room.get("type"))
        by_type.setdefault(room_type, []).append(poly)
    return polys, by_type


def _build_walkable_polygon(rooms: Sequence[Mapping[str, Any]]):
    from shapely.ops import unary_union

    polys, by_type = _room_polygons(rooms)
    if not polys:
        return None, by_type
    return unary_union(polys), by_type


def _default_cell_size(bounds: Tuple[float, float, float, float]) -> float:
    min_x, min_y, max_x, max_y = bounds
    span = max(max_x - min_x, max_y - min_y, 1.0)
    return max(4.0, min(10.0, span / 40.0))


def _build_grid(walkable, cell_size: float | None = None) -> _Grid:
    from shapely.geometry import Point
    from shapely.prepared import prep

    min_x, min_y, max_x, max_y = walkable.bounds
    cell = float(cell_size or _default_cell_size(walkable.bounds))
    xs = []
    ys = []
    x = min_x + cell / 2.0
    while x <= max_x - cell / 2.0 + 1e-6:
        xs.append(x)
        x += cell
    y = min_y + cell / 2.0
    while y <= max_y - cell / 2.0 + 1e-6:
        ys.append(y)
        y += cell

    prepared = prep(walkable)
    mask: List[List[bool]] = []
    for y in ys:
        row = []
        for x in xs:
            row.append(prepared.contains(Point(x, y)))
        mask.append(row)

    return _Grid(xs=xs, ys=ys, mask=mask, cell_size=cell, origin=(min_x, min_y))


def _nearest_walkable(grid: _Grid, point: Tuple[float, float]) -> Tuple[int, int] | None:
    if not grid.xs or not grid.ys:
        return None
    x, y = point
    ix = min(range(len(grid.xs)), key=lambda i: abs(grid.xs[i] - x))
    iy = min(range(len(grid.ys)), key=lambda i: abs(grid.ys[i] - y))

    if grid.mask[iy][ix]:
        return iy, ix

    max_radius = max(len(grid.xs), len(grid.ys))
    for radius in range(1, max_radius):
        y_min = max(0, iy - radius)
        y_max = min(len(grid.ys) - 1, iy + radius)
        x_min = max(0, ix - radius)
        x_max = min(len(grid.xs) - 1, ix + radius)
        for ty in range(y_min, y_max + 1):
            for tx in range(x_min, x_max + 1):
                if grid.mask[ty][tx]:
                    return ty, tx
    return None


def _grid_to_point(grid: _Grid, node: Tuple[int, int]) -> Tuple[float, float]:
    y_idx, x_idx = node
    return grid.xs[x_idx], grid.ys[y_idx]


def _neighbors(grid: _Grid, node: Tuple[int, int]) -> Iterable[Tuple[int, int]]:
    y_idx, x_idx = node
    candidates = [
        (y_idx - 1, x_idx),
        (y_idx + 1, x_idx),
        (y_idx, x_idx - 1),
        (y_idx, x_idx + 1),
    ]
    for ny, nx in candidates:
        if 0 <= ny < len(grid.ys) and 0 <= nx < len(grid.xs) and grid.mask[ny][nx]:
            yield ny, nx


def _astar_path(
    grid: _Grid,
    start: Tuple[int, int],
    goal: Tuple[int, int],
) -> List[Tuple[int, int]]:
    import heapq

    def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_set: List[Tuple[float, Tuple[int, int]]] = []
    heapq.heappush(open_set, (0.0, start))
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score = {start: 0.0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor in _neighbors(grid, current):
            tentative = g_score[current] + 1.0
            if tentative < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f_score = tentative + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor))

    return []


def _chaikin_smooth(
    points: List[Tuple[float, float]],
    iterations: int = 2,
) -> List[Tuple[float, float]]:
    if len(points) < 3:
        return points
    result = points
    for _ in range(iterations):
        new_points = [result[0]]
        for p0, p1 in zip(result, result[1:]):
            qx = 0.75 * p0[0] + 0.25 * p1[0]
            qy = 0.75 * p0[1] + 0.25 * p1[1]
            rx = 0.25 * p0[0] + 0.75 * p1[0]
            ry = 0.25 * p0[1] + 0.75 * p1[1]
            new_points.extend([(qx, qy), (rx, ry)])
        new_points.append(result[-1])
        result = new_points
    return result


def _path_to_cells(grid: _Grid, points: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
    cells: List[Tuple[int, int]] = []
    for x, y in points:
        ix = min(range(len(grid.xs)), key=lambda i: abs(grid.xs[i] - x))
        iy = min(range(len(grid.ys)), key=lambda i: abs(grid.ys[i] - y))
        if grid.mask[iy][ix]:
            cells.append((iy, ix))
    return cells


def _build_masks(grid: _Grid, polygons: Iterable[Any]) -> List[List[bool]]:
    from shapely.geometry import Point
    from shapely.prepared import prep
    from shapely.ops import unary_union

    polys = list(polygons)
    if not polys:
        return [[False for _ in grid.xs] for _ in grid.ys]
    union = unary_union(polys)
    prepared = prep(union)
    mask = []
    for y in grid.ys:
        row = []
        for x in grid.xs:
            row.append(prepared.contains(Point(x, y)))
        mask.append(row)
    return mask


def _largest_zero_component(mask: List[List[bool]], traffic: List[List[int]]) -> int:
    visited = [[False for _ in row] for row in mask]
    max_size = 0
    for y in range(len(mask)):
        for x in range(len(mask[0])):
            if visited[y][x] or not mask[y][x] or traffic[y][x] > 0:
                continue
            stack = [(y, x)]
            visited[y][x] = True
            size = 0
            while stack:
                cy, cx = stack.pop()
                size += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if (
                        0 <= ny < len(mask)
                        and 0 <= nx < len(mask[0])
                        and not visited[ny][nx]
                        and mask[ny][nx]
                        and traffic[ny][nx] == 0
                    ):
                        visited[ny][nx] = True
                        stack.append((ny, nx))
            max_size = max(max_size, size)
    return max_size


def _sum_mask(mask: List[List[bool]]) -> int:
    return sum(1 for row in mask for val in row if val)


def _sum_mask_with_traffic(mask: List[List[bool]], traffic: List[List[int]]) -> int:
    return sum(
        1
        for y, row in enumerate(mask)
        for x, val in enumerate(row)
        if val and traffic[y][x] > 0
    )


def score_path_simulation(
    rooms: Sequence[Mapping[str, Any]],
    openings: Sequence[Mapping[str, Any]],
    *,
    enable_dev_plot: bool = False,
    output_dir: str | None = None,
) -> Tuple[float, Dict[str, Any]]:
    diagnostics: Dict[str, Any] = {
        "paths": [],
        "warnings": [],
    }

    try:
        walkable, by_type = _build_walkable_polygon(rooms)
        if walkable is None or walkable.is_empty:
            return 0.0, {**diagnostics, "warnings": ["no_walkable_area"]}

        grid = _build_grid(walkable)
    except Exception as exc:  # pragma: no cover - geometry guard
        return 0.0, {**diagnostics, "warnings": [f"geometry_error: {exc}"]}

    room_index = _build_room_index(rooms)

    main_doors = [
        o for o in openings if _opening_type(o.get("opening_type")) == "maindoor"
    ]
    internal_doors = [
        o for o in openings if _opening_type(o.get("opening_type")) == "internaldoor"
    ]

    entry_points: List[Tuple[float, float]] = []
    for opening in main_doors:
        midpoint = _door_midpoint(opening)
        if midpoint is not None:
            entry_points.append(midpoint)

    if not entry_points:
        diagnostics["warnings"].append("missing_main_door")

    def room_entrances(room_type: str) -> List[Tuple[float, float]]:
        points: List[Tuple[float, float]] = []
        for opening in internal_doors:
            room_name = _normalize_str(opening.get("room_name"))
            room = room_index.get(room_name)
            if room is None:
                continue
            if _normalize_str(room.get("type")) != room_type:
                continue
            midpoint = _door_midpoint(opening)
            if midpoint is not None:
                points.append(midpoint)
        if points:
            return points

        for room in rooms:
            if _normalize_str(room.get("type")) == room_type:
                points.append(_room_center(room))
        return points

    kitchen_points = room_entrances("kitchen")
    bedroom_points = room_entrances("bedroom")
    bathroom_points = room_entrances("bathroom")

    routes: List[Tuple[str, Tuple[float, float], Tuple[float, float]]] = []

    for entry in entry_points:
        for kitchen in kitchen_points:
            routes.append(("entry_to_kitchen", entry, kitchen))
        for bedroom in bedroom_points:
            routes.append(("entry_to_bedroom", entry, bedroom))
        for bathroom in bathroom_points:
            routes.append(("entry_to_bathroom", entry, bathroom))

    for bedroom in bedroom_points:
        if bathroom_points:
            closest_bath = min(
                bathroom_points,
                key=lambda p: (p[0] - bedroom[0]) ** 2 + (p[1] - bedroom[1]) ** 2,
            )
            routes.append(("bedroom_to_bathroom", bedroom, closest_bath))
        if kitchen_points:
            closest_kitchen = min(
                kitchen_points,
                key=lambda p: (p[0] - bedroom[0]) ** 2 + (p[1] - bedroom[1]) ** 2,
            )
            routes.append(("bedroom_to_kitchen", bedroom, closest_kitchen))

    if not routes:
        diagnostics["warnings"].append("no_routes")

    paths: List[Dict[str, Any]] = []
    traffic = [[0 for _ in grid.xs] for _ in grid.ys]

    for kind, start_pt, end_pt in routes:
        start_node = _nearest_walkable(grid, start_pt)
        end_node = _nearest_walkable(grid, end_pt)
        if start_node is None or end_node is None:
            diagnostics["warnings"].append(f"route_unreachable:{kind}")
            continue
        node_path = _astar_path(grid, start_node, end_node)
        if not node_path:
            diagnostics["warnings"].append(f"path_not_found:{kind}")
            continue
        polyline = [_grid_to_point(grid, node) for node in node_path]
        smoothed = _chaikin_smooth(polyline, iterations=2)
        cells = _path_to_cells(grid, smoothed)
        for cy, cx in cells:
            traffic[cy][cx] += 1
        paths.append(
            {
                "kind": kind,
                "start": start_pt,
                "end": end_pt,
                "polyline": smoothed,
            }
        )

    living_polys = by_type.get("livingroom", [])
    bedroom_polys = by_type.get("bedroom", [])
    hallway_polys = by_type.get("hallway", [])

    living_mask = _build_masks(grid, living_polys)
    bedroom_mask = _build_masks(grid, bedroom_polys)
    hallway_mask = _build_masks(grid, hallway_polys)

    living_area = _sum_mask(living_mask) * (grid.cell_size ** 2)
    path_cells = sum(1 for row in traffic for val in row if val > 0)
    path_area = path_cells * (grid.cell_size ** 2)

    circulation_ratio = path_area / living_area if living_area > 1e-6 else 0.0
    circulation_score = (
        max(0.0, min(1.0, 1.0 - (circulation_ratio / 0.3)))
        if living_area > 0
        else 0.5
    )

    breach_paths = [p for p in paths if p["kind"] == "entry_to_bathroom"]
    breach_count = 0
    if breach_paths and bedroom_points:
        threshold = grid.cell_size * 1.5
        for path in breach_paths:
            breached = False
            for x, y in path["polyline"]:
                for bx, by in bedroom_points:
                    if (x - bx) ** 2 + (y - by) ** 2 <= threshold ** 2:
                        breached = True
                        break
                if breached:
                    break
            if breached:
                breach_count += 1
    privacy_score = (
        1.0 if not breach_paths else max(0.0, 1.0 - breach_count / len(breach_paths))
    )

    hallway_total = _sum_mask(hallway_mask)
    hallway_used = _sum_mask_with_traffic(hallway_mask, traffic)
    hallway_utility = hallway_used / hallway_total if hallway_total > 0 else 1.0

    living_bed_mask = [
        [living_mask[y][x] or bedroom_mask[y][x] for x in range(len(grid.xs))]
        for y in range(len(grid.ys))
    ]
    largest_quiet = _largest_zero_component(living_bed_mask, traffic)
    living_bed_total = _sum_mask(living_bed_mask)
    furniture_flex = living_bed_total > 0 and largest_quiet / living_bed_total or 0.5

    metric_scores = {
        "circulation_efficiency": circulation_score,
        "privacy_breach": privacy_score,
        "hallway_utility": hallway_utility,
        "furniture_flexibility": furniture_flex,
    }

    weighted_score = sum(metric_scores.values()) / len(metric_scores) if metric_scores else 0.0
    total_score = max(0.0, min(10.0, weighted_score * 10.0))

    diagnostics.update(
        {
            "path_count": len(paths),
            "route_count": len(routes),
            "grid_cell_size": grid.cell_size,
            "metrics": metric_scores,
            "metric_values": {
                "circulation_ratio": circulation_ratio,
                "hallway_utility": hallway_utility,
                "privacy_breach_count": breach_count,
                "living_area": living_area,
            },
            "paths": [
                {"kind": p["kind"], "point_count": len(p["polyline"])}
                for p in paths
            ],
        }
    )

    if enable_dev_plot:
        try:
            from .dev.plotter import save_path_simulation_plot

            output_dir = output_dir or "test/outputs/path_score"
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
            makedirs(output_dir, exist_ok=True)
            output_path = f"{output_dir}/{timestamp}.png"
            save_path_simulation_plot(
                output_path=output_path,
                walkable=walkable,
                room_polys_by_type=by_type,
                paths=paths,
                grid=grid,
                traffic=traffic,
                hallway_mask=hallway_mask,
            )
            diagnostics["plot_file"] = output_path
        except Exception as exc:  # pragma: no cover - best-effort debug
            diagnostics["warnings"].append(f"plot_error: {exc}")

    return total_score, diagnostics
