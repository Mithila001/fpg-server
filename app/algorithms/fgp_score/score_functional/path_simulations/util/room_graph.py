"""Room connectivity graph for path simulation.

Builds a graph where:
  - Nodes = rooms (by room_name) + "OUTSIDE" virtual node
  - Edges = door openings (the only legal passage between rooms)

Dijkstra finds the optimal room sequence, then a world-coordinate
polyline is built:  start_centroid -> door_approach -> door_mid ->
door_exit -> next_room_centroid -> ...

Chaikin smoothing is then applied to produce natural curved paths.

No imports from outside this package.
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from ._dev_print import dev_print

_WorldPt = Tuple[float, float]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_door(opening: Any) -> bool:
    return "door" in str(_get(opening, "opening_type", "")).lower()


def _door_midpoint(opening: Any) -> _WorldPt:
    x1 = float(_get(opening, "x1", 0.0))
    y1 = float(_get(opening, "y1", 0.0))
    x2 = float(_get(opening, "x2", 0.0))
    y2 = float(_get(opening, "y2", 0.0))
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _room_centroid(room: Any) -> _WorldPt:
    verts: List[_WorldPt] = _get(room, "vertices", [])
    if not verts:
        return (0.0, 0.0)
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _dist(a: _WorldPt, b: _WorldPt) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _offset_towards(origin: _WorldPt, target: _WorldPt, dist: float) -> _WorldPt:
    """Return a point `dist` cm from origin towards target."""
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    d = math.sqrt(dx * dx + dy * dy)
    if d < 1e-6:
        return origin
    return (origin[0] + dx / d * dist, origin[1] + dy / d * dist)


def chaikin_smooth(pts: List[_WorldPt], iterations: int = 3) -> List[_WorldPt]:
    """Chaikin corner-cutting — produces natural curved paths."""
    if len(pts) < 3:
        return pts
    for _ in range(iterations):
        new_pts: List[_WorldPt] = [pts[0]]
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            new_pts.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
            new_pts.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
        new_pts.append(pts[-1])
        pts = new_pts
    return pts


# ---------------------------------------------------------------------------
# Door edge
# ---------------------------------------------------------------------------


class DoorEdge:
    """One door connecting two rooms."""

    __slots__ = ("room_a", "room_b", "midpoint", "opening_type")

    def __init__(
        self,
        room_a: str,
        room_b: str,
        midpoint: _WorldPt,
        opening_type: str,
    ) -> None:
        self.room_a = room_a
        self.room_b = room_b
        self.midpoint = midpoint
        self.opening_type = opening_type

    def other(self, room_name: str) -> str:
        return self.room_b if room_name == self.room_a else self.room_a

    def __repr__(self) -> str:
        return f"Door({self.room_a}<->{self.room_b} @ {self.midpoint})"


# ---------------------------------------------------------------------------
# Room graph
# ---------------------------------------------------------------------------


class RoomGraph:
    """Room connectivity graph.  Nodes = room names.  Edges = DoorEdges."""

    def __init__(self) -> None:
        self._adj: Dict[str, List[DoorEdge]] = defaultdict(list)
        self._centroids: Dict[str, _WorldPt] = {}
        self._room_types: Dict[str, str] = {}

    # -- construction -------------------------------------------------------

    def add_room(self, name: str, centroid: _WorldPt, room_type: str) -> None:
        if name not in self._centroids:
            self._centroids[name] = centroid
            self._room_types[name] = room_type
            if name not in self._adj:
                self._adj[name] = []

    def add_door(self, edge: DoorEdge) -> None:
        self._adj[edge.room_a].append(edge)
        self._adj[edge.room_b].append(edge)

    # -- accessors ----------------------------------------------------------

    def get_centroid(self, room_name: str) -> Optional[_WorldPt]:
        return self._centroids.get(room_name)

    def get_room_type(self, room_name: str) -> str:
        return self._room_types.get(room_name, "unknown")

    @property
    def all_rooms(self) -> List[str]:
        return list(self._adj.keys())

    def neighbors(self, room_name: str) -> List[Tuple[str, DoorEdge]]:
        return [(e.other(room_name), e) for e in self._adj.get(room_name, [])]

    # -- pathfinding --------------------------------------------------------

    def find_path(
        self,
        start_room: str,
        end_room: str,
        door_approach_cm: float = 20.0,
        smooth_iterations: int = 3,
    ) -> Optional[List[_WorldPt]]:
        """Return a smoothed world-coordinate path from start_room to end_room.

        Returns None if no route exists.
        Waypoints: start_centroid -> (approach + midpoint + exit per door) -> end_centroid
        """
        if start_room not in self._adj or end_room not in self._adj:
            dev_print("path", f"Room not in graph: {start_room!r} or {end_room!r}")
            return None

        if start_room == end_room:
            c = self._centroids.get(start_room)
            return [c] if c else None

        # Dijkstra on room graph
        dist_map: Dict[str, float] = {start_room: 0.0}
        prev: Dict[str, Tuple[str, DoorEdge]] = {}
        queue: List[Tuple[float, str]] = [(0.0, start_room)]
        visited: Set[str] = set()

        while queue:
            d, current = heapq.heappop(queue)
            if current in visited:
                continue
            visited.add(current)
            if current == end_room:
                break
            c_curr = self._centroids.get(current, (0.0, 0.0))
            for neighbor, edge in self.neighbors(current):
                c_nb = self._centroids.get(neighbor, (0.0, 0.0))
                new_d = d + _dist(c_curr, c_nb)
                if new_d < dist_map.get(neighbor, float("inf")):
                    dist_map[neighbor] = new_d
                    prev[neighbor] = (current, edge)
                    heapq.heappush(queue, (new_d, neighbor))

        if end_room not in prev:
            dev_print("path", f"No graph path: {start_room} -> {end_room}")
            return None

        # Reconstruct room + edge sequence
        room_seq: List[str] = []
        edge_seq: List[DoorEdge] = []
        node = end_room
        while node != start_room:
            p_room, p_edge = prev[node]
            room_seq.append(node)
            edge_seq.append(p_edge)
            node = p_room
        room_seq.append(start_room)
        room_seq.reverse()
        edge_seq.reverse()

        dev_print("path", f"Room sequence: {' -> '.join(room_seq)}")

        # Build raw waypoints with approach/exit offsets at each door
        # Pattern: start_c -> [approach_a, door_mid, approach_b] per door -> end_c
        raw: List[_WorldPt] = []
        start_c = self._centroids.get(start_room, (0.0, 0.0))
        raw.append(start_c)

        for i, edge in enumerate(edge_seq):
            room_before = room_seq[i]
            room_after = room_seq[i + 1]
            c_before = self._centroids.get(room_before, (0.0, 0.0))
            c_after = self._centroids.get(room_after, (0.0, 0.0))
            door_mid = edge.midpoint

            # Approach: point inside room_before, near door
            approach = _offset_towards(door_mid, c_before, door_approach_cm)
            # Exit: point inside room_after, near door
            exit_pt = _offset_towards(door_mid, c_after, door_approach_cm)

            raw.append(approach)
            raw.append(door_mid)
            raw.append(exit_pt)

        end_c = self._centroids.get(end_room, (0.0, 0.0))
        raw.append(end_c)

        # Smooth for natural human-like path
        smoothed = chaikin_smooth(raw, iterations=smooth_iterations)
        return smoothed


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_room_graph(rooms: List[Any], openings: List[Any]) -> RoomGraph:
    """Build RoomGraph from room list and opening list."""
    graph = RoomGraph()

    for room in rooms:
        name = str(_get(room, "name", "")).strip()
        rtype = str(_get(room, "type", "")).strip()
        centroid = _room_centroid(room)
        if name:
            graph.add_room(name, centroid, rtype)

    # Virtual OUTSIDE node
    graph.add_room("OUTSIDE", (0.0, 0.0), "outside")

    for op in openings:
        if not _is_door(op):
            continue
        rn = str(_get(op, "room_name", "")).strip()
        crn = str(_get(op, "connected_room_name", "")).strip()
        otype = str(_get(op, "opening_type", "")).strip()
        mid = _door_midpoint(op)

        if not rn or not crn:
            continue

        # Ensure nodes exist (might not be in rooms list, e.g. OUTSIDE)
        if rn not in graph.all_rooms:
            graph.add_room(rn, mid, "unknown")
        if crn not in graph.all_rooms:
            graph.add_room(crn, mid, "unknown")

        edge = DoorEdge(rn, crn, mid, otype)
        graph.add_door(edge)
        dev_print("path", f"Graph edge: {edge}")

    dev_print("path", f"Room graph built: {len(graph.all_rooms)} nodes, edges per room: "
              f"{ {r: len(graph.neighbors(r)) for r in graph.all_rooms} }")
    return graph
