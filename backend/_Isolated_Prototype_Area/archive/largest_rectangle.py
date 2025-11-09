"""
largest_rectangle.py

Complete, standalone setup to find the largest axis-aligned rectangle fully contained
inside a (simple, not self-intersecting) polygon.

Features:
- Robust handling of sweep-line vertex/tie cases using epsilon.
- Returns rectangle in original polygon coordinates (inverse transform included).
- Simple matplotlib plotting fallback (if you have a custom plotter, you can replace it).
- CLI example at bottom.

Usage:
    python largest_rectangle.py

Note: This is written to be copy/paste-ready. If you want the code split into
multiple files (e.g., main.py + myUtilities.py) say so and I'll split it.

Author: generated for you — nerdy mentor mode enabled.
"""

import math
import sys
from typing import List, Tuple, Optional, Sequence

from typing import Any
plt: Any = None
try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    HAS_MPL = False

Point = Tuple[float, float]
ProfileSlice = dict

# ------------------------- Utilities (robust) -------------------------

def calculate_distance(p1: Point, p2: Point = (0.0, 0.0)) -> float:
    x1, y1 = p1
    x2, y2 = p2
    return math.hypot(x2 - x1, y2 - y1)


def find_active_segment(chain: List[Point], y_sweep: float, eps: float = 1e-9) -> Optional[Tuple[Point, Point]]:
    """
    Find the segment (p1,p2) in 'chain' that the horizontal line y = y_sweep intersects.
    This function is tolerant to vertex hits and horizontal segments.

    The chain is expected to be ordered either bottom->top or top->bottom.
    We prefer the rule: include the segment when y_sweep is in (min_y - eps, max_y + eps]
    and favor consistent tie-breaking to avoid double counting at vertices.
    """
    if not chain or len(chain) < 2:
        return None

    # Decide orientation by comparing first two distinct-y points
    is_upwards_chain = None
    for i in range(len(chain) - 1):
        if not math.isclose(chain[i][1], chain[i + 1][1], abs_tol=eps):
            is_upwards_chain = chain[i][1] < chain[i + 1][1]
            break
    if is_upwards_chain is None:
        # all y identical (degenerate); no valid segment for sweep
        return None

    for i in range(len(chain) - 1):
        p1 = chain[i]
        p2 = chain[i + 1]
        y1 = p1[1]
        y2 = p2[1]

        y_min_seg = min(y1, y2) - eps
        y_max_seg = max(y1, y2) + eps

        # If sweep exactly equals a horizontal segment's y, we treat horizontal specially
        if math.isclose(y1, y2, abs_tol=eps):
            # horizontal segment: consider it active if y_sweep is close and
            # return the left-to-right ordering consistently (p1 as left)
            if abs(y_sweep - y1) <= eps:
                # return points in the order they appear — caller's interpolation handles x
                return p1, p2
            else:
                continue

        # general case: include the segment if y_sweep is in (y_min, y_max] (with eps)
        if (y_min_seg < y_sweep) and (y_sweep <= y_max_seg):
            # Tie-break to ensure consistent selection at vertices:
            # If chain is upwards, prefer segment where p1 is lower and p2 is higher.
            if is_upwards_chain:
                # require p1.y <= y_sweep <= p2.y (with eps)
                if (p1[1] - eps) <= y_sweep <= (p2[1] + eps):
                    return p1, p2
            else:
                # chain is downwards; p1 is upper, p2 lower
                if (p2[1] - eps) <= y_sweep <= (p1[1] + eps):
                    return p1, p2

    return None


def get_x_intersection(p1: Point, p2: Point, y_sweep: float, eps: float = 1e-9) -> Optional[float]:
    (x1, y1) = p1
    (x2, y2) = p2

    # horizontal segment: return the left-most x (deterministic)
    if abs(y2 - y1) <= eps:
        # return min x to be conservative (contained by polygon)
        return min(x1, x2)

    dy = y2 - y1
    ratio = (y_sweep - y1) / dy
    # if ratio slightly out of [0,1] due to numeric issues, clamp it
    if ratio < -eps or ratio > 1.0 + eps:
        return None
    ratio = max(0.0, min(1.0, ratio))

    dx = x2 - x1
    x_intersect = x1 + ratio * dx
    return x_intersect


# ------------------- Geometry transforms (rotate/translate) -------------------

def translate_and_reorder_polygon(polygon_coordinates: Sequence[Point], TA: Tuple[Point, Point]):

    """
    Translate polygon so chosen pivot (closest of TA endpoints to origin) becomes (0,0)
    and reorder polygon list to start at that pivot. Returns (reordered, pivot_point).
    """
    point_A, point_T = TA
    dist_A = calculate_distance(point_A)
    dist_T = calculate_distance(point_T)
    pivot_point = point_A if dist_A <= dist_T else point_T

    try:
        pivot_index = polygon_coordinates.index(pivot_point)
    except ValueError:
        # pivot not exactly in vertex list; find closest vertex instead
        pivot_index = min(range(len(polygon_coordinates)), key=lambda i: calculate_distance(polygon_coordinates[i], pivot_point))
        pivot_point = polygon_coordinates[pivot_index]

    Px, Py = pivot_point
    translated = [(x - Px, y - Py) for (x, y) in polygon_coordinates]

    # reorder so pivot is first
    reordered = translated[pivot_index:] + translated[:pivot_index]
    return reordered, pivot_point


def rotate_polygon_to_x_axis(translated_polygon: Sequence[Point], TA: Tuple[Point, Point], pivot_point: Point) -> Tuple[List[Point], float]:

    """
    Compute rotation to align TA with X-axis.
    The TA endpoints must be translated already relative to pivot_point.
    Returns rotated polygon and rotation angle (radians).
    """
    # find the other endpoint of TA in translated coords
    # TA may contain absolute coords; compute translated TA vector
    A_abs, T_abs = TA
    # find which of A_abs/T_abs equals pivot_point
    if calculate_distance(A_abs, pivot_point) < 1e-9:
        other = T_abs
    elif calculate_distance(T_abs, pivot_point) < 1e-9:
        other = A_abs
    else:
        # fallback: pick the one closer to origin after translation
        translated_t = [(x - pivot_point[0], y - pivot_point[1]) for (x, y) in (A_abs, T_abs)]
        other = A_abs if calculate_distance(translated_t[0]) < calculate_distance(translated_t[1]) else T_abs

    xT = other[0] - pivot_point[0]
    yT = other[1] - pivot_point[1]

    current_angle = math.atan2(yT, xT)
    rotation_angle = -current_angle
    cos_t = math.cos(rotation_angle)
    sin_t = math.sin(rotation_angle)

    rotated = [(x * cos_t - y * sin_t, x * sin_t + y * cos_t) for (x, y) in translated_polygon]
    return rotated, rotation_angle


def inverse_rotate_point(pt: Point, rotation_angle: float) -> Point:
    cos_t = math.cos(-rotation_angle)
    sin_t = math.sin(-rotation_angle)
    x, y = pt
    return (x * cos_t - y * sin_t, x * sin_t + y * cos_t)


def inverse_translate_point(pt: Point, pivot_point: Point) -> Point:
    px, py = pivot_point
    x, y = pt
    return (x + px, y + py)


def transform_rectangle_back(rect_coords_rotated: List[Point], rotation_angle: float, pivot_point: Point) -> List[Point]:
    rect_original = []
    for p in rect_coords_rotated:
        unrot = inverse_rotate_point(p, rotation_angle)
        untrans = inverse_translate_point(unrot, pivot_point)
        rect_original.append(untrans)
    return rect_original


# --------------------- Polygon chain splitting & sweep ---------------------

def split_polygon_chains(coordinates: List[Point], eps: float = 1e-9):
    # start at bottom-most, then left-most
    min_point = coordinates[0]
    start_index = 0
    for i, (x, y) in enumerate(coordinates):
        if y < min_point[1] - eps or (math.isclose(y, min_point[1], abs_tol=eps) and x < min_point[0]):
            min_point = (x, y)
            start_index = i
    y_min = min_point[1]

    N = len(coordinates)
    ordered = [coordinates[(start_index + i) % N] for i in range(N)]

    # find first occurrence of y_max
    y_max = ordered[0][1]
    y_max_index = 0
    for i, (x, y) in enumerate(ordered):
        if y > y_max + eps:
            y_max = y
            y_max_index = i

    left_chain_raw = ordered[:y_max_index + 1]
    right_chain_raw = ordered[y_max_index:]

    right_chain = right_chain_raw[1:]
    if len(right_chain) > 1 and math.isclose(right_chain[-1][1], y_min, abs_tol=eps):
        right_chain.pop()

    def remove_vertical_redundancy(chain):
        if not chain:
            return []
        cleaned = [chain[0]]
        for i in range(1, len(chain)):
            if not math.isclose(chain[i][1], cleaned[-1][1], abs_tol=eps):
                cleaned.append(chain[i])
        return cleaned

    left_chain = remove_vertical_redundancy(left_chain_raw)
    right_chain = remove_vertical_redundancy(right_chain)

    if len(left_chain) < 2 or len(right_chain) < 2:
        print("Warning: chains may be too short for safe sweeping")

    return left_chain, right_chain, y_min, y_max


def sweep_line_width_profile(left_chain: List[Point], right_chain: List[Point], min_y: float, max_y: float,
                             y_resolution: float = 0.5, min_width: float = 0.0, eps: float = 1e-9) -> List[ProfileSlice]:
    cross_sections = []
    i = min_y  # start exactly at min_y
    # guard against invalid range
    if max_y < min_y:
        return cross_sections

    while i <= max_y + eps:
        left_seg = find_active_segment(left_chain, i, eps=eps)
        right_seg = find_active_segment(right_chain, i, eps=eps)

        if left_seg and right_seg:
            x_left = get_x_intersection(left_seg[0], left_seg[1], i, eps=eps)
            x_right = get_x_intersection(right_seg[0], right_seg[1], i, eps=eps)
            if x_left is not None and x_right is not None:
                w = x_right - x_left
                if w >= min_width - eps:
                    cross_sections.append({'y': i, 'x_left': x_left, 'x_right': x_right, 'width': w})
        i += y_resolution
    return cross_sections


def find_max_area_rectangle(cross_sections_data: List[ProfileSlice], min_height: float = 0.5,
                            min_width: float = 0.5, eps: float = 1e-9):
    if not cross_sections_data:
        return {'max_area': 0.0, 'width': 0.0, 'height': 0.0, 'y_bottom_index': -1, 'y_top_index': -1}

    max_area = 0.0
    best_result = {'max_area': 0.0, 'width': 0.0, 'height': 0.0, 'y_bottom_index': -1, 'y_top_index': -1}
    N = len(cross_sections_data)

    for i in range(N):
        y_bottom = cross_sections_data[i]['y']
        max_x_left = cross_sections_data[i]['x_left']
        min_x_right = cross_sections_data[i]['x_right']

        for j in range(i + 1, N):
            data_j = cross_sections_data[j]
            # update boundaries
            if data_j['x_left'] > max_x_left:
                max_x_left = data_j['x_left']
            if data_j['x_right'] < min_x_right:
                min_x_right = data_j['x_right']

            local_width = min_x_right - max_x_left
            if local_width < min_width - eps:
                break

            local_height = data_j['y'] - y_bottom
            if local_height < min_height - eps:
                continue

            area = local_width * local_height
            if area > max_area + eps:
                max_area = area
                best_result.update({'max_area': area, 'width': local_width, 'height': local_height,
                                    'y_bottom_index': i, 'y_top_index': j})
    return best_result


def get_rectangle_coordinates(best_result: dict, sweep_marks: List[ProfileSlice]) -> List[Point]:
    i = best_result['y_bottom_index']
    j = best_result['y_top_index']
    if i < 0 or j < 0:
        return []

    y_bottom = sweep_marks[i]['y']
    y_top = sweep_marks[j]['y']

    max_x_left = sweep_marks[i]['x_left']
    min_x_right = sweep_marks[i]['x_right']

    for k in range(i, j + 1):
        s = sweep_marks[k]
        if s['x_left'] > max_x_left:
            max_x_left = s['x_left']
        if s['x_right'] < min_x_right:
            min_x_right = s['x_right']

    # rectangle corners in rotated/transformed space
    return [(max_x_left, y_bottom), (min_x_right, y_bottom), (min_x_right, y_top), (max_x_left, y_top)]


# ---------------------- Plotting helper ----------------------

def plot_polygons(polygon_list: Sequence[Sequence[Point]], title: str = "Polygons"):

    if not HAS_MPL:
        print("Matplotlib not available, skipping plotting.")
        return
    plt.figure(figsize=(6, 6))
    for poly in polygon_list:
        if not poly:
            continue
        xs = [p[0] for p in poly] + [poly[0][0]]
        ys = [p[1] for p in poly] + [poly[0][1]]
        plt.plot(xs, ys, '-o')
    plt.gca().set_aspect('equal', 'box')
    plt.title(title)
    plt.show()


# ---------------------- Example / main driver ----------------------

def example_run():
    originalPolygon = [(1, 7), (-4, 5), (-5, -1), (-2, -6), (3, -4), (6, 2)]
    TA_line = (originalPolygon[0], originalPolygon[1])

    # Parameters
    Y_RES = 0.25
    MIN_W = 0.01
    MIN_H = 0.01

    print("--- RUN: user polygon ---")
    zeroed_polygon, pivot = translate_and_reorder_polygon(originalPolygon, TA_line)
    print("zeroed_polygon:", zeroed_polygon)
    rotated_polygon, angle = rotate_polygon_to_x_axis(zeroed_polygon, TA_line, pivot)
    print("rotated_polygon:", rotated_polygon)

    left_chain, right_chain, y_min, y_max = split_polygon_chains(rotated_polygon)
    print("left_chain:", left_chain)
    print("right_chain:", right_chain)
    print("y_min, y_max:", y_min, y_max)

    # Quick validations
    print("len(left_chain), len(right_chain)", len(left_chain), len(right_chain))
    if y_max < y_min:
        print("WARNING: y_max < y_min after splitting — swapping them for sweep.")
        y_min, y_max = min(y_min, y_max), max(y_min, y_max)

    # Show which segments are active for the first few sweep lines
    print("\nSweep diagnostics (first 40 steps):")
    step = 0
    i = y_min
    while i <= y_max + 1e-9 and step < 40:
        left_seg = find_active_segment(left_chain, i)
        right_seg = find_active_segment(right_chain, i)
        print(f"y={i:.4f} -> left_seg={left_seg}, right_seg={right_seg}")
        i += Y_RES
        step += 1

    cross_section_data = sweep_line_width_profile(left_chain, right_chain, min_y=y_min, max_y=y_max,
                                                  y_resolution=Y_RES, min_width=MIN_W)
    print("Sweep slices:", len(cross_section_data))

    best_rectangle = find_max_area_rectangle(cross_section_data, min_height=MIN_H, min_width=MIN_W)
    rect_rotated = get_rectangle_coordinates(best_rectangle, cross_section_data)

    if rect_rotated:
        rect_original = transform_rectangle_back(rect_rotated, angle, pivot)
    else:
        rect_original = []

    print("Best rectangle (area,width,height):", best_rectangle['max_area'], best_rectangle['width'], best_rectangle['height'])
    print("Rectangle original coords:", rect_original)

    # --- CONTROL TEST: simple axis-aligned rectangle (this must work) ---
    print("\n--- CONTROL TEST: axis-aligned rectangle ---")
    simple_rect = [(1, 7), (-4, 5), (-5, -1), (-2, -6), (3, -4), (6, 2)]
    TA_line_simple = (simple_rect[0], simple_rect[1])
    zp_simple, p_simple = translate_and_reorder_polygon(simple_rect, TA_line_simple)
    rot_simple, ang_simple = rotate_polygon_to_x_axis(zp_simple, TA_line_simple, p_simple)
    lc_s, rc_s, ymin_s, ymax_s = split_polygon_chains(rot_simple)
    slices_s = sweep_line_width_profile(lc_s, rc_s, ymin_s, ymax_s, y_resolution=0.25, min_width=0.01)
    best_s = find_max_area_rectangle(slices_s, min_height=0.01, min_width=0.01)
    rect_rot_s = get_rectangle_coordinates(best_s, slices_s)
    rect_orig_s = transform_rectangle_back(rect_rot_s, ang_simple, p_simple) if rect_rot_s else []
    print("control slices:", len(slices_s), " best:", best_s)
    print("control rect coords:", rect_orig_s)




def main(argv):
    example_run()


if __name__ == '__main__':
    main(sys.argv)
