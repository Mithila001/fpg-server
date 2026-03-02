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

__all__ = [
    "UsableSpaceFinder",
]


class UsableSpaceFinder:
    """
    Public API class. Instantiate and call :py:meth:`find_buildable_space` to
    compute a polygon that respects individual edge offsets.  This mirrors
    the previous module-level ``find_buildable_space`` function but provides
    an object-oriented style consistent with :class:`FPBoundaryFinder`.

    Internally it delegates to :class:`_UsableSpaceFinder` which contains the
    original algorithm implementation.
    """

    def __init__(self) -> None:
        self._impl = _UsableSpaceFinder()

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

        result = self._impl.compute_buildable_vertices(vertices, offsets)
        print("Returning Buildable Vertices: ", result)
        return result


class _UsableSpaceFinder:
    """
    Internal class that contains the algorithm to compute buildable space
    from a polygon and per-edge offsets.

    All methods mirror the original procedural functions but are methods
    so the implementation is organized as an object. This class is intended
    to remain internal (name starts with underscore).
    """

    def __init__(self) -> None:
        pass

    def _initialize_land_space_calculations(
        self, polygon_edges: List[Dict[str, float]]
    ) -> List[Dict[str, float]]:
        """
        Calculates the line-equation parameters (ax + by = C) for each
        polygon edge, offset by its specified 'OffsetDistance'.
        """
        offset_line_parameters: List[Dict[str, float]] = []

        for edge in polygon_edges:
            sx = edge["StartVertex_x"]
            sy = edge["StartVertex_y"]
            ex = edge["EndVertex_x"]
            ey = edge["EndVertex_y"]
            offset = edge["OffsetDistance"]

            # 1. Derive Edge Vector
            vec_x = ex - sx
            vec_y = ey - sy

            # 2. Calculate Outward Normal Vector (90-degree clockwise)
            normal_x = vec_y
            normal_y = -vec_x

            # 3. Normalize the Normal Vector
            magnitude = math.sqrt(normal_x**2 + normal_y**2)
            norm_nx = 0.0
            norm_ny = 0.0

            if magnitude > 0:
                norm_nx = normal_x / magnitude
                norm_ny = normal_y / magnitude

            # 4. Calculate 'C' for the new offset line
            c_offset = (norm_nx * sx) + (norm_ny * sy) + offset

            line_params = {"a": norm_nx, "b": norm_ny, "C": c_offset}

            offset_line_parameters.append(line_params)

        return offset_line_parameters

    def _create_land_edges(
        self, vertices: List[Tuple[float, float]], offset_distances: List[float]
    ) -> List[Dict[str, float]]:
        """
        Creates the 'land_edges' list from a list of vertices and a corresponding
        list of offset distances for each edge.
        """
        land_edges: List[Dict[str, float]] = []
        num_vertices = len(vertices)

        if num_vertices != len(offset_distances):
            print("Error: The number of vertices must equal the number of offsets.")
            return []

        for i in range(num_vertices):
            # Get the start vertex
            start_vertex_x = vertices[i][0]
            start_vertex_y = vertices[i][1]

            # Get the end vertex, looping back to the start for the last edge
            end_vertex_index = (i + 1) % num_vertices
            end_vertex_x = vertices[end_vertex_index][0]
            end_vertex_y = vertices[end_vertex_index][1]

            # Get the offset distance for this specific edge
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

    def _find_intersection(
        self, line1: Dict[str, float], line2: Dict[str, float]
    ) -> Optional[Tuple[float, float]]:
        """
        Helper to find the (x, y) intersection point of two lines using Cramer's rule:
            a1*x + b1*y = C1
            a2*x + b2*y = C2
        Returns None when lines are parallel (or nearly so).
        """
        a1 = line1["a"]
        b1 = line1["b"]
        C1 = line1["C"]

        a2 = line2["a"]
        b2 = line2["b"]
        C2 = line2["C"]

        # Calculate the determinant
        D = (a1 * b2) - (a2 * b1)

        # If D is zero, lines are parallel or the same
        if abs(D) < 1e-9:  # Using a small number to avoid floating point issues
            print("Warning: Lines are parallel and do not intersect.")
            return None

        # Calculate Dx and Dy for Cramer's rule
        Dx = (C1 * b2) - (C2 * b1)
        Dy = (a1 * C2) - (a2 * C1)

        # Calculate the intersection point
        x = Dx / D
        y = Dy / D

        return (x, y)

    def _find_intersection_vertices(
        self, offset_lines: List[Dict[str, float]]
    ) -> List[Tuple[float, float]]:
        """
        Takes the list of offset line parameters (ax + by = C) and calculates
        the new polygon vertices by finding the intersection of adjacent lines.
        """
        new_vertices: List[Tuple[float, float]] = []
        num_lines = len(offset_lines)

        if num_lines < 2:
            print("Error: Need at least 2 lines to find intersections.")
            return []

        for i in range(num_lines):
            # Get the first line
            line1 = offset_lines[i]

            # Get the second line, looping back to the start for the last vertex
            line2_index = (i + 1) % num_lines
            line2 = offset_lines[line2_index]

            # Find the intersection of line_i and line_i+1
            intersection_point = self._find_intersection(line1, line2)

            if intersection_point:
                new_vertices.append(intersection_point)

        return new_vertices

    def compute_buildable_vertices(
        self, vertices: List[Tuple[float, float]], offsets: List[float]
    ) -> List[Tuple[float, float]]:
        """
        Main method that wires up the steps to compute the buildable vertices.
        This mirrors the original procedural `find_buildable_space` logic.
        """
        land_edges = self._create_land_edges(vertices, offsets)
        offset_lines = self._initialize_land_space_calculations(land_edges)
        buildable_vertices = self._find_intersection_vertices(offset_lines)
        return buildable_vertices


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
