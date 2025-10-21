import math


def calculate_distance(p1, p2=(0, 0)):
    """Calculates the Euclidean distance between two points."""
    x1, y1 = p1
    x2, y2 = p2
    # The basic distance formula: sqrt((x2-x1)^2 + (y2-y1)^2)
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)