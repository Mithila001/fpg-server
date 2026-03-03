#!/usr/bin/env python3
"""
usable_land_space_finder.py

Object-oriented implementation that computes a polygon respecting
individual per-edge setback offsets.
Public API is exposed via the ``UsableSpaceFinder`` class.
"""

from typing import List, Tuple, Dict, Optional
import math

__all__ = [
    "UsableSpaceFinder",
]


class UsableSpaceFinder:
    """
    Public API class. Instantiate and call :py:meth:`find_buildable_space` to
    compute a polygon that respects individual edge offsets.
    """

    def __init__(self) -> None:
        self._impl = _UsableSpaceFinder()

    def find_buildable_space(
        self, vertices: List[Tuple[float, float]], offsets: List[float]
    ) -> List[Tuple[float, float]]:
        """Compute buildable vertices from polygon vertices and per-edge offsets.

        Args:
            vertices: List of (x, y) coordinate pairs defining the land polygon.
            offsets:  Per-edge setback distances (one per edge, same length as vertices).

        Returns:
            List of (x, y) pairs defining the buildable/usable polygon.
        """
        result = self._impl.compute_buildable_vertices(vertices, offsets)
        return result


class _UsableSpaceFinder:
    """
    Internal class containing the algorithm to compute buildable space
    from a polygon and per-edge offsets.
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
            raise ValueError(
                f"Number of vertices ({num_vertices}) must equal number of offsets "
                f"({len(offset_distances)})."
            )

        for i in range(num_vertices):
            start_vertex_x = vertices[i][0]
            start_vertex_y = vertices[i][1]

            end_vertex_index = (i + 1) % num_vertices
            end_vertex_x = vertices[end_vertex_index][0]
            end_vertex_y = vertices[end_vertex_index][1]

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
        Helper to find the (x, y) intersection point of two lines using Cramer's rule.
        Returns None when lines are parallel.
        """
        a1, b1, C1 = line1["a"], line1["b"], line1["C"]
        a2, b2, C2 = line2["a"], line2["b"], line2["C"]

        D = (a1 * b2) - (a2 * b1)

        if abs(D) < 1e-9:
            return None

        Dx = (C1 * b2) - (C2 * b1)
        Dy = (a1 * C2) - (a2 * C1)

        return (Dx / D, Dy / D)

    def _find_intersection_vertices(
        self, offset_lines: List[Dict[str, float]]
    ) -> List[Tuple[float, float]]:
        """
        Takes the list of offset line parameters and calculates new polygon
        vertices by finding the intersection of adjacent lines.
        """
        new_vertices: List[Tuple[float, float]] = []
        num_lines = len(offset_lines)

        if num_lines < 2:
            return []

        for i in range(num_lines):
            line1 = offset_lines[i]
            line2 = offset_lines[(i + 1) % num_lines]
            intersection_point = self._find_intersection(line1, line2)

            if intersection_point:
                new_vertices.append(intersection_point)

        return new_vertices

    def compute_buildable_vertices(
        self, vertices: List[Tuple[float, float]], offsets: List[float]
    ) -> List[Tuple[float, float]]:
        """
        Main method: wires up the steps to compute the buildable vertices.
        """
        land_edges = self._create_land_edges(vertices, offsets)
        offset_lines = self._initialize_land_space_calculations(land_edges)
        buildable_vertices = self._find_intersection_vertices(offset_lines)
        return buildable_vertices
