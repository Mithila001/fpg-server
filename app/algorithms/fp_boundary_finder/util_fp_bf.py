import math


class PolygonGeomUtils:
    """Geometry utility methods for polygon transformations used by FPBoundaryFinder."""

    @staticmethod
    def _calculate_distance(p1, p2=(0, 0)):
        """Calculates the Euclidean distance between two points."""
        x1, y1 = p1
        x2, y2 = p2
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @staticmethod
    def _find_active_segment(chain, y_sweep):
        """
        Finds the segment (p1, p2) in a chain that the sweep line y_sweep crosses.
        """
        is_upwards_chain = chain[0][1] < chain[1][1]

        for i in range(len(chain) - 1):
            p1 = chain[i]
            p2 = chain[i + 1]

            y1 = p1[1]
            y2 = p2[1]

            y_min_seg = min(y1, y2)
            y_max_seg = max(y1, y2)

            if y_min_seg < y_sweep <= y_max_seg:
                if is_upwards_chain:
                    if y1 < y_sweep <= y2:
                        return p1, p2
                else:
                    if y2 < y_sweep <= y1:
                        return p1, p2

        return None

    @staticmethod
    def _get_x_intersection(p1, p2, y_sweep):
        """
        Calculates the X-coordinate where the horizontal sweep line (y_sweep)
        intersects the line segment defined by (p1, p2).
        """
        (x1, y1) = p1
        (x2, y2) = p2

        if math.isclose(y1, y2):
            return x1

        dy = y2 - y1
        ratio = (y_sweep - y1) / dy
        dx = x2 - x1

        return x1 + ratio * dx

    @staticmethod
    def _flip_xy_coordinates(coordinates):
        """Swaps the X and Y coordinates for every point in the list: (x, y) -> (y, x)."""
        return [(y, x) for x, y in coordinates]

    @staticmethod
    def _inverse_rotate_polygon(coordinates, rotation_angle):
        """Rotates the coordinates by -rotation_angle (the inverse rotation)."""
        inverse_angle = -rotation_angle
        cos_theta = math.cos(inverse_angle)
        sin_theta = math.sin(inverse_angle)

        return [
            (x * cos_theta - y * sin_theta, x * sin_theta + y * cos_theta)
            for x, y in coordinates
        ]

    @staticmethod
    def _inverse_translate_polygon(coordinates, TA):
        """
        Translates the coordinates back to original world space using the TA pivot.
        """
        point_A = TA[0]
        point_T = TA[1]

        dist_A = PolygonGeomUtils._calculate_distance(point_A)
        dist_T = PolygonGeomUtils._calculate_distance(point_T)

        pivot_point = point_A if dist_A <= dist_T else point_T
        (Px, Py) = pivot_point

        return [(x + Px, y + Py) for x, y in coordinates]

    @staticmethod
    def _move_polygon_to_positive_axis(polygon_coordinates):
        """
        Moves the polygon to the positive X and Y axes (first quadrant).
        """
        if not polygon_coordinates:
            return [], (0.0, 0.0)

        min_x = min(x for x, y in polygon_coordinates)
        min_y = min(y for x, y in polygon_coordinates)

        dx = -min_x if min_x < -1e-9 else (-min_x if 0 > min_x >= -1e-9 else 0.0)
        dy = -min_y if min_y < -1e-9 else (-min_y if 0 > min_y >= -1e-9 else 0.0)

        move_points = (dx, dy)
        moved_polygon = [(x + dx, y + dy) for x, y in polygon_coordinates]

        return moved_polygon, move_points

    @staticmethod
    def _reset_polygon_position(polygon_coordinates, move_points):
        """
        Resets a polygon's position by subtracting the move_points vector.
        """
        if not polygon_coordinates:
            return []

        dx, dy = move_points
        return [(x - dx, y - dy) for x, y in polygon_coordinates]
