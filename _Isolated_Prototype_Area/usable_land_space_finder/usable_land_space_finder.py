#!/usr/bin/env python3
"""
usable_space_finder.py

Object-oriented refactor of the original procedural implementation.
Public API is now exposed solely via the ``UsableSpaceFinder`` class.
(A former module-level ``find_buildable_space`` helper has been removed
from the public interface; a commented stub remains at the bottom for
historical reference.)
"""

from typing import List, Tuple, Dict, Optional
import math

__all__ = ["UsableSpaceFinder"]


class UsableSpaceFinder:
    """
    Public API class. Instantiate and call :py:meth:`find_buildable_space` to
    compute a polygon that respects individual edge offsets.  This mirrors
    the previous module-level ``find_buildable_space`` function but provides
    an object-oriented style consistent with :class:`FPBoundaryFinder`.

    All implementation details are private methods of this class; only
    ``find_buildable_space`` is part of the public interface.  A convenience
    module-level function of the same name is also exported.
    """

    def find_buildable_space(
        self, vertices: List[Tuple[float, float]], offsets: List[float]
    ) -> List[Tuple[float, float]]:
        """Compute buildable vertices and print diagnostic messages.

        Arguments match the standalone function: ``vertices`` is a list of
        ``(x, y)`` pairs and ``offsets`` is either a single value or a
        per-edge list.  The diagnostics behaviour is kept for backwards
        compatibility.
        """
        print("\n=== Start Algorithm: Find Buildable Space ===")
        print("Given Vertices: ", vertices)
        print("Given Offsets:  ", offsets)

        result = self._compute_buildable_vertices(vertices, offsets)
        print("Returning Buildable Vertices: ", result)
        return result

    # Private helper methods follow

    def _compute_buildable_vertices(
        self, vertices: List[Tuple[float, float]], offsets: List[float]
    ) -> List[Tuple[float, float]]:
        """Core logic previously in _UsableSpaceFinder."""
        land_edges = self._create_land_edges(vertices, offsets)
        offset_lines = self._initialize_land_space_calculations(land_edges)
        return self._find_intersection_vertices(offset_lines)

    def _create_land_edges(
        self, vertices: List[Tuple[float, float]], offset_distances: List[float]
    ) -> List[Dict[str, float]]:
        """Build edge dictionaries from vertices and offsets."""
        land_edges: List[Dict[str, float]] = []
        num_vertices = len(vertices)

        if num_vertices != len(offset_distances):
            print("Error: The number of vertices must equal the number of offsets.")
            return []

        for i in range(num_vertices):
            start_vertex_x, start_vertex_y = vertices[i]
            end_vertex_index = (i + 1) % num_vertices
            end_vertex_x, end_vertex_y = vertices[end_vertex_index]
            offset = offset_distances[i]

            edge = {
                "StartVertex_x": start_vertex_x,
                "StartVertex_y": start_vertex_y,
                "EndVertex_x": end_vertex_x,
                "EndVertex_y": end_vertex_y,
                "OffsetDistance": offset,
            }
            land_edges.append(edge)

        return land_edges

    def _initialize_land_space_calculations(
        self, polygon_edges: List[Dict[str, float]]
    ) -> List[Dict[str, float]]:
        """Compute (a,b,C) parameters for offset lines."""
        offset_line_parameters: List[Dict[str, float]] = []

        for edge in polygon_edges:
            sx = edge["StartVertex_x"]
            sy = edge["StartVertex_y"]
            ex = edge["EndVertex_x"]
            ey = edge["EndVertex_y"]
            offset = edge["OffsetDistance"]

            # Edge vector
            vec_x = ex - sx
            vec_y = ey - sy

            # Outward normal (90° clockwise)
            normal_x = vec_y
            normal_y = -vec_x

            magnitude = math.hypot(normal_x, normal_y)
            norm_nx = normal_x / magnitude if magnitude > 0 else 0.0
            norm_ny = normal_y / magnitude if magnitude > 0 else 0.0

            c_offset = (norm_nx * sx) + (norm_ny * sy) + offset

            offset_line_parameters.append({"a": norm_nx, "b": norm_ny, "C": c_offset})

        return offset_line_parameters

    def _find_intersection(
        self, line1: Dict[str, float], line2: Dict[str, float]
    ) -> Optional[Tuple[float, float]]:
        """Return intersection point of two lines in ax+by=C form."""
        a1, b1, C1 = line1["a"], line1["b"], line1["C"]
        a2, b2, C2 = line2["a"], line2["b"], line2["C"]

        D = (a1 * b2) - (a2 * b1)
        if abs(D) < 1e-9:
            print("Warning: Lines are parallel and do not intersect.")
            return None

        Dx = (C1 * b2) - (C2 * b1)
        Dy = (a1 * C2) - (a2 * C1)
        return (Dx / D, Dy / D)

    def _find_intersection_vertices(
        self, offset_lines: List[Dict[str, float]]
    ) -> List[Tuple[float, float]]:
        """Calculate vertices from adjacent offset line intersections."""
        new_vertices: List[Tuple[float, float]] = []
        num_lines = len(offset_lines)

        if num_lines < 2:
            print("Error: Need at least 2 lines to find intersections.")
            return []

        for i in range(num_lines):
            l1 = offset_lines[i]
            l2 = offset_lines[(i + 1) % num_lines]
            pt = self._find_intersection(l1, l2)
            if pt:
                new_vertices.append(pt)

        return new_vertices


# NOTE: The original procedural wrapper used to live here.  It has been
# disabled and removed from ``__all__`` because the class-based API is now
# preferred.  The code is retained in comments purely for historical
# reference and can be un-commented if backwards compatibility is required.
#
# def find_buildable_space(
#     vertices: List[Tuple[float, float]], offsets: List[float]
# ) -> List[Tuple[float, float]]:
#     """
#     Legacy module-level convenience wrapper.  Delegates to
#     :class:`UsableSpaceFinder` while preserving the original
#     diagnostic printouts.

#     ``UsableSpaceFinder`` is the preferred interface for new code, but
#     this function remains available for backwards compatibility and for
#     scripts that previously imported it directly.
#     """
#     # simple delegation; the class method already prints diagnostics
#     return UsableSpaceFinder().find_buildable_space(vertices, offsets)
