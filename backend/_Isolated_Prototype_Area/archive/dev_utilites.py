def get_cross_section_coordinates(data: list[dict]) -> list[tuple[float, float]]:
    """
    Takes cross-section data (list of dicts with 'y', 'x_left', 'x_right')
    and returns a list of coordinates (tuples) tracing the perimeter.

    The coordinates trace the perimeter in this order:
    1. Up the left side (bottom to top).
    2. Down the right side (top to bottom).

    Args:
        data: A list of dictionaries, typically ordered from lowest 'y' to highest 'y'.

    Returns:
        A list of (x, y) coordinate tuples representing the cross-section perimeter.
    """
    if not data:
        return []

    # 1. Left boundary coordinates (bottom to top)
    # [(x_left, y), ...]
    left_coords = [(item['x_left'], item['y']) for item in data]

    # 2. Right boundary coordinates (top to bottom)
    # Reverse the data to get the path from top-right to bottom-right
    # [(x_right, y), ...] in reverse order
    right_coords = [(item['x_right'], item['y']) for item in reversed(data)]

    # Combine the two lists to form the closed perimeter
    # The last point of the left side (top-left) connects to the first point of the right side (top-right).
    # The last point of the right side (bottom-right) closes the shape with the first point of the left side (bottom-left).
    perimeter_coords = left_coords + right_coords

    return perimeter_coords