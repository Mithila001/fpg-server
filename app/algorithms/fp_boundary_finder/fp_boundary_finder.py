import math

from .util_fp_bf import PolygonGeomUtils


class FPBoundaryFinder:
    """
    Finds the largest inscribed axis-aligned rectangles (parallel and
    perpendicular to the first edge) within a given polygon.
    """

    def __init__(self, y_resolution: float = 0.1):
        """
        Args:
            y_resolution: Step size for the horizontal sweep line. Smaller values
                          give higher precision at the cost of performance.
        """
        self._y_resolution = y_resolution

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def fp_boundary_finder(
        self,
        polygon_coordinates: list,
        TA_line: tuple,
        min_width: float = 100,
        min_height: float = 100,
    ):
        """
        Finds the largest valid buildable rectangles inside the given polygon.

        Args:
            polygon_coordinates: Ordered list of (x, y) vertices.
            TA_line: Orientation line segment ((x1, y1), (x2, y2)) or
                     (x1, y1, x2, y2).
            min_width:  Minimum acceptable rectangle width.
            min_height: Minimum acceptable rectangle height.

        Returns:
            List of 4 (x, y) points for the largest candidate rectangle.
        """
        return self._run(polygon_coordinates, TA_line, min_width, min_height)

    # ------------------------------------------------------------------ #
    #  Private Pipeline Steps                                              #
    # ------------------------------------------------------------------ #

    def _run(self, polygon_coordinates, TA_line, min_width, min_height):
        TA_line = self._normalize_ta_line(TA_line)

        zeroed_polygon, TA_zeroed = self._translate_and_reorder_polygon(
            polygon_coordinates, TA_line
        )
        rotated_polygon, angle = self._rotate_polygon_to_x_axis(
            zeroed_polygon, TA_zeroed
        )
        positive_polygon, moved_axis_values = (
            PolygonGeomUtils._move_polygon_to_positive_axis(rotated_polygon)
        )

        largest_rect_parallel = self._sweep_for_best_rectangle(
            positive_polygon, min_width, min_height
        )

        flipped = PolygonGeomUtils._flip_xy_coordinates(positive_polygon)
        largest_rect_perp_raw = self._sweep_for_best_rectangle(
            flipped, min_width, min_height
        )
        largest_rect_perpendicular = PolygonGeomUtils._flip_xy_coordinates(
            largest_rect_perp_raw
        )

        rect_parallel_repositioned = PolygonGeomUtils._reset_polygon_position(
            largest_rect_parallel, moved_axis_values
        )
        rect_perp_repositioned = PolygonGeomUtils._reset_polygon_position(
            largest_rect_perpendicular, moved_axis_values
        )

        rect_parallel_oriented = PolygonGeomUtils._inverse_rotate_polygon(
            rect_parallel_repositioned, angle
        )
        rect_perp_oriented = PolygonGeomUtils._inverse_rotate_polygon(
            rect_perp_repositioned, angle
        )

        final_rect_parallel = PolygonGeomUtils._inverse_translate_polygon(
            rect_parallel_oriented, TA_line
        )
        final_rect_perpendicular = PolygonGeomUtils._inverse_translate_polygon(
            rect_perp_oriented, TA_line
        )

        parallel_area = self._rectangle_area(final_rect_parallel)
        perpendicular_area = self._rectangle_area(final_rect_perpendicular)

        if perpendicular_area > parallel_area:
            return final_rect_perpendicular
        return final_rect_parallel

    def _normalize_ta_line(self, TA_line):
        if isinstance(TA_line, (list, tuple)) and len(TA_line) == 4:
            x1, y1, x2, y2 = TA_line
            return ((x1, y1), (x2, y2))

        if (
            isinstance(TA_line, (list, tuple))
            and len(TA_line) == 2
            and all(isinstance(pt, (list, tuple)) and len(pt) == 2 for pt in TA_line)
        ):
            return (tuple(TA_line[0]), tuple(TA_line[1]))

        raise ValueError(
            "TA_line must be ((x1, y1), (x2, y2)) or (x1, y1, x2, y2)."
        )

    def _rectangle_area(self, rectangle):
        if not rectangle:
            return 0.0

        xs = [p[0] for p in rectangle]
        ys = [p[1] for p in rectangle]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        return max(width, 0.0) * max(height, 0.0)

    def _translate_and_reorder_polygon(self, polygon_coordinates, TA):
        point_A = TA[0]
        point_B = TA[1]

        dist_A = PolygonGeomUtils._calculate_distance(point_A)
        dist_B = PolygonGeomUtils._calculate_distance(point_B)

        if dist_A <= dist_B:
            pivot_point = point_A
            non_pivot_point = point_B
        else:
            pivot_point = point_B
            non_pivot_point = point_A

        (Px, Py) = pivot_point
        dx = -Px
        dy = -Py

        (Tx, Ty) = non_pivot_point
        TA_Zeroed = (Tx + dx, Ty + dy)

        try:
            pivot_index = polygon_coordinates.index(pivot_point)
        except ValueError:
            pivot_index = 0

        translated = [(x + dx, y + dy) for x, y in polygon_coordinates]
        reordered = translated[pivot_index:] + translated[:pivot_index]

        return reordered, TA_Zeroed

    def _rotate_polygon_to_x_axis(self, translated_polygon, TA):
        dx_T, dy_T = TA
        current_angle = math.atan2(dy_T, dx_T)
        rotation_angle = -current_angle

        cos_theta = math.cos(rotation_angle)
        sin_theta = math.sin(rotation_angle)

        rotated = [
            (x * cos_theta - y * sin_theta, x * sin_theta + y * cos_theta)
            for x, y in translated_polygon
        ]

        return rotated, rotation_angle

    def _split_polygon_chains(self, coordinates):
        bottom_coord = min(coordinates, key=lambda c: (c[1], c[0]))

        idx = coordinates.index(bottom_coord)
        rotated = coordinates[idx:] + coordinates[:idx]

        def _signed_area(poly):
            a = 0.0
            n = len(poly)
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % n]
                a += x1 * y2 - x2 * y1
            return a / 2.0

        area = _signed_area(rotated)
        if area > 0:
            rev = rotated[::-1]
            ridx = rev.index(bottom_coord)
            rotated_clockwise = rev[ridx:] + rev[:ridx]
        else:
            rotated_clockwise = rotated

        y_vals = [y for _, y in rotated_clockwise]
        min_y = min(y_vals)
        max_y = max(y_vals)

        first_max_idx = next(
            (i for i, (_, y) in enumerate(rotated_clockwise) if y >= max_y), None
        )

        if first_max_idx is None:
            left_chain = rotated_clockwise[:]
            right_chain = []
        else:
            left_chain = rotated_clockwise[:first_max_idx] + [
                rotated_clockwise[first_max_idx]
            ]
            right_chain = rotated_clockwise[first_max_idx:]
            right_chain.append(rotated_clockwise[0])

        return left_chain, right_chain, min_y, max_y

    def _sweep_line_width_profile(
        self, left_chain, right_chain, min_y, max_y, min_width
    ):
        cross_sections_data = []
        i = min_y + self._y_resolution

        while i <= max_y:
            left_segment = PolygonGeomUtils._find_active_segment(left_chain, i)
            right_segment = PolygonGeomUtils._find_active_segment(right_chain, i)

            if left_segment and right_segment:
                x_left = PolygonGeomUtils._get_x_intersection(
                    left_segment[0], left_segment[1], i
                )
                x_right = PolygonGeomUtils._get_x_intersection(
                    right_segment[0], right_segment[1], i
                )
                w = x_right - x_left

                if w >= min_width:
                    cross_sections_data.append(
                        {"y": i, "x_left": x_left, "x_right": x_right, "width": w}
                    )

            i += self._y_resolution

        return cross_sections_data

    def _find_max_area_rectangle(self, cross_sections_data, min_height, min_width):
        max_area = 0.0
        best_result = {
            "max_area": 0.0,
            "width": 0.0,
            "height": 0.0,
            "y_bottom_index": -1,
            "y_top_index": -1,
        }

        N = len(cross_sections_data)

        for i in range(N):
            y_bottom = cross_sections_data[i]["y"]
            max_x_left = cross_sections_data[i]["x_left"]
            min_x_right = cross_sections_data[i]["x_right"]

            for j in range(i, N):
                y_top = cross_sections_data[j]["y"]
                top_line_data = cross_sections_data[j]

                if top_line_data["x_left"] > max_x_left:
                    max_x_left = top_line_data["x_left"]

                if top_line_data["x_right"] < min_x_right:
                    min_x_right = top_line_data["x_right"]

                local_width = min_x_right - max_x_left
                local_height = y_top - y_bottom

                if local_height < min_height:
                    continue

                area = local_width * local_height

                if area > max_area:
                    max_area = area
                    best_result["max_area"] = area
                    best_result["width"] = local_width
                    best_result["height"] = local_height
                    best_result["y_bottom_index"] = i
                    best_result["y_top_index"] = j

        return best_result

    def _get_rectangle_coordinates(self, best_result, sweep_marks):
        if not sweep_marks:
            return []

        y_bottom_index = best_result["y_bottom_index"]
        y_top_index = best_result["y_top_index"]

        if y_bottom_index < 0 or y_top_index < 0:
            return []

        y_bottom = sweep_marks[y_bottom_index]["y"]
        y_top = sweep_marks[y_top_index]["y"]

        max_x_left = sweep_marks[y_bottom_index]["x_left"]
        min_x_right = sweep_marks[y_bottom_index]["x_right"]

        for k in range(y_bottom_index, y_top_index + 1):
            slice_data = sweep_marks[k]
            if slice_data["x_left"] > max_x_left:
                max_x_left = slice_data["x_left"]
            if slice_data["x_right"] < min_x_right:
                min_x_right = slice_data["x_right"]

        return [
            (max_x_left, y_bottom),
            (min_x_right, y_bottom),
            (min_x_right, y_top),
            (max_x_left, y_top),
        ]

    def _sweep_for_best_rectangle(self, polygon, min_width, min_height):
        left_chain, right_chain, y_min, y_max = self._split_polygon_chains(polygon)
        cross_section_data = self._sweep_line_width_profile(
            left_chain, right_chain, min_y=y_min, max_y=y_max, min_width=min_width
        )
        if not cross_section_data:
            return []

        best_rectangle = self._find_max_area_rectangle(
            cross_section_data, min_height=min_height, min_width=min_width
        )
        return self._get_rectangle_coordinates(best_rectangle, cross_section_data)
