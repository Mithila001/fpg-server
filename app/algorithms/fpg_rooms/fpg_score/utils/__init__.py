from .adjacency_geometry import interval_overlap_len, strict_axis_overlap, touches_with_min_overlap
from .pocket_geometry import (
    extract_contact_points,
    is_close_to_any,
    iter_polygons,
    iter_segments,
    segment_orientation,
)

__all__ = [
    "extract_contact_points",
    "interval_overlap_len",
    "is_close_to_any",
    "iter_polygons",
    "iter_segments",
    "segment_orientation",
    "strict_axis_overlap",
    "touches_with_min_overlap",
]