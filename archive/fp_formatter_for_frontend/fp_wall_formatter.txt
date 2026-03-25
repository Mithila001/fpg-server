from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from app.algorithms.floor_plan_generator.generator import FloorPlanGenerator  # noqa: F401
from app.services.algorithm_manager import RoomData, run_fpg

# Type aliases
WallSegment = Tuple[Tuple[float, float], Tuple[float, float]]
RoomLabel = Dict[str, Any]


class FpFormatter:
    """Transforms room polygons into a welded wireframe wall layout.

    Pipeline (per the algorithm sketch):

    1. **Grid snap** — normalise all coordinates to ``snap_precision``.
    2. **Axis decompose** — split polygons into horizontal / vertical segments
       keyed by their shared axis coordinate.
    3. **Vertex inject** — propagate T-junction points so perpendicular walls
       that terminate mid-segment create a clean joint.
    4. **Fragment & validate** — break each axis into micro-segments; retain
       only those fully covered by at least one original room interval.

    Args:
        snap_precision: Rounding unit for coordinate normalisation (default 0.1).
    """

    def __init__(self, snap_precision: float = 0.1) -> None:
        self._snap_precision = snap_precision
        self._wall_segments: List[WallSegment] = []
        self._room_labels: List[RoomLabel] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_walls(
        self,
        polygons: List[List[Tuple[float, float]]],
        room_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Run the wall-welding pipeline on *polygons*.

        Args:
            polygons: One polygon per room — each a list of (x, y) vertices.
                Rectangles produced by the floor-plan generator have four
                vertices ordered CCW: BL → BR → TR → TL.
            room_metadata: Optional list of room dicts with at least the keys
                ``name``, ``type``, ``x``, ``y``, ``w``, ``h``.  Used to
                compute text-label anchor points for the UI.
        """
        snapped = [self._snap_polygon(poly) for poly in polygons]

        h_segs, v_segs = self._build_axis_dicts(snapped)
        h_verts, v_verts = self._inject_vertices(h_segs, v_segs)

        walls: List[WallSegment] = []

        for y_axis, intervals in h_segs.items():
            walls.extend(
                self._fragment_and_validate(
                    y_axis, h_verts[y_axis], intervals, is_horizontal=True
                )
            )

        for x_axis, intervals in v_segs.items():
            walls.extend(
                self._fragment_and_validate(
                    x_axis, v_verts[x_axis], intervals, is_horizontal=False
                )
            )

        self._wall_segments = walls

        if room_metadata is not None:
            self._room_labels = [
                {
                    "name": r["name"],
                    "type": r["type"],
                    "center": (r["x"] + r["w"] / 2, r["y"] + r["h"] / 2),
                }
                for r in room_metadata
            ]

    def run_fpg_and_compute(
        self,
        width: Optional[float] = None,
        height: Optional[float] = None,
        rooms_data: Optional[List[RoomData]] = None,
    ) -> None:
        """Run the floor-plan generator then immediately compute walls.

        Room metadata (name, type, and label position) is extracted
        automatically from the generator's solution.

        Args:
            width: Floor plan width; generator default applies when ``None``.
            height: Floor plan height; generator default applies when ``None``.
            rooms_data: Room specs; generator defaults apply when ``None``.
        """
        kwargs: Dict[str, Any] = {}
        if width is not None:
            kwargs["width"] = width
        if height is not None:
            kwargs["height"] = height
        if rooms_data is not None:
            kwargs["rooms_data"] = rooms_data

        polygons, generator = run_fpg(**kwargs)
        metadata = generator.get_solution() if polygons else []
        self.compute_walls(polygons, room_metadata=metadata)

    def get_wall_segments(self) -> List[WallSegment]:
        """Return unique wall segments from the last pipeline run.

        Each segment is a pair of (x, y) tuples: ``((x1, y1), (x2, y2))``.
        An empty list means no walls have been computed yet.
        """
        return self._wall_segments

    def get_room_labels(self) -> List[RoomLabel]:
        """Return room label data from the last pipeline run.

        Each entry is a dict with keys ``name``, ``type``, and ``center``
        (an (x, y) tuple at the room's geometric centre).
        """
        return self._room_labels

    def get_result(self) -> Dict[str, Any]:
        """Return walls and room labels together as a single dict.

        Returns:
            ``{"walls": [...], "rooms": [...]}``
        """
        return {
            "walls": self._wall_segments,
            "rooms": self._room_labels,
        }

    # ------------------------------------------------------------------
    # Private pipeline — Step 1: Grid snapping
    # ------------------------------------------------------------------

    def _snap(self, value: float) -> float:
        p = self._snap_precision
        return round(round(value / p) * p, 10)

    def _snap_polygon(
        self, polygon: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        return [(self._snap(x), self._snap(y)) for x, y in polygon]

    # ------------------------------------------------------------------
    # Private pipeline — Step 2: Axis-aligned decomposition
    # ------------------------------------------------------------------

    def _build_axis_dicts(
        self,
        polygons: List[List[Tuple[float, float]]],
    ) -> Tuple[
        Dict[float, List[Tuple[float, float]]],
        Dict[float, List[Tuple[float, float]]],
    ]:
        """Decompose snapped polygons into horizontal and vertical segments.

        Returns:
            h_segs: ``{y: [(x_min, x_max), ...]}``
            v_segs: ``{x: [(y_min, y_max), ...]}``
        """
        h_segs: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
        v_segs: Dict[float, List[Tuple[float, float]]] = defaultdict(list)

        for poly in polygons:
            n = len(poly)
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % n]

                if y1 == y2:  # horizontal edge
                    h_segs[y1].append((min(x1, x2), max(x1, x2)))
                elif x1 == x2:  # vertical edge
                    v_segs[x1].append((min(y1, y2), max(y1, y2)))
                # Non-axis-aligned edges are not expected for rectangular rooms

        return dict(h_segs), dict(v_segs)

    # ------------------------------------------------------------------
    # Private pipeline — Step 3: Vertex injection
    # ------------------------------------------------------------------

    def _inject_vertices(
        self,
        h_segs: Dict[float, List[Tuple[float, float]]],
        v_segs: Dict[float, List[Tuple[float, float]]],
    ) -> Tuple[Dict[float, Set[float]], Dict[float, Set[float]]]:
        """Inject T-junction vertices across crossing axes.

        For every horizontal axis Y, any vertical segment whose endpoint
        equals Y contributes its X key into ``h_verts[Y]`` — and vice-versa
        for vertical axes.

        Returns:
            h_verts: ``{y: {x_coord, ...}}``
            v_verts: ``{x: {y_coord, ...}}``
        """
        # Seed each axis with the endpoints that already exist on it.
        h_verts: Dict[float, Set[float]] = {
            y: {x for interval in intervals for x in interval}
            for y, intervals in h_segs.items()
        }
        v_verts: Dict[float, Set[float]] = {
            x: {y for interval in intervals for y in interval}
            for x, intervals in v_segs.items()
        }

        # Inject V-segment X-coords into the H axes they touch.
        for x_key, intervals in v_segs.items():
            for y_start, y_end in intervals:
                for y_axis in h_verts:
                    if y_axis == y_start or y_axis == y_end:
                        h_verts[y_axis].add(x_key)

        # Inject H-segment Y-coords into the V axes they touch.
        for y_key, intervals in h_segs.items():
            for x_start, x_end in intervals:
                for x_axis in v_verts:
                    if x_axis == x_start or x_axis == x_end:
                        v_verts[x_axis].add(y_key)

        return h_verts, v_verts

    # ------------------------------------------------------------------
    # Private pipeline — Step 4: Fragment & validate
    # ------------------------------------------------------------------

    def _fragment_and_validate(
        self,
        axis_coord: float,
        vertices: Set[float],
        original_intervals: List[Tuple[float, float]],
        is_horizontal: bool,
    ) -> List[WallSegment]:
        """Break an axis into micro-segments; keep only room-covered ones.

        A candidate segment (pᵢ, pᵢ₊₁) is retained when at least one
        original room interval fully contains it:
        ``any(orig_start <= pᵢ  and  orig_end >= pᵢ₊₁)``.

        Args:
            axis_coord: The fixed Y (horizontal) or X (vertical) coordinate.
            vertices: All points on this axis after vertex injection.
            original_intervals: The raw (min, max) room-edge intervals on
                this axis — used to validate coverage.
            is_horizontal: ``True`` for H axes, ``False`` for V axes.

        Returns:
            List of validated wall segments as ``((x1, y1), (x2, y2))`` tuples.
        """
        sorted_pts = sorted(vertices)
        result: List[WallSegment] = []

        for i in range(len(sorted_pts) - 1):
            p_a = sorted_pts[i]
            p_b = sorted_pts[i + 1]

            covered = any(
                orig_s <= p_a and orig_e >= p_b
                for orig_s, orig_e in original_intervals
            )
            if not covered:
                continue

            if is_horizontal:
                result.append(((p_a, axis_coord), (p_b, axis_coord)))
            else:
                result.append(((axis_coord, p_a), (axis_coord, p_b)))

        return result


# module-level convenience instance
# Prefer instantiating FpFormatter() directly when isolation is needed.
formatter = FpFormatter()
