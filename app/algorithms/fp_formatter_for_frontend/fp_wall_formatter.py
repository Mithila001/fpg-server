from __future__ import annotations

from typing import Any, Dict, Tuple

from app.algorithms.floor_plan_generator.generator import FloorPlanGenerator  # noqa: F401

# Type aliases
WallSegment = Tuple[Tuple[float, float], Tuple[float, float]]
RoomLabel = Dict[str, Any]

# placeholder for formatter output; refine when actual structure is known
FormattedLayout = Any


class FpFormatter:
    def __init__(self, snap_precision: float = 0.1) -> None:
        """Create a new formatter.

        Args:
            snap_precision: grid spacing used by :meth:`_snap_to_grid`.
        """
        self._snap_precision = snap_precision

    # Main Entry Function
    def fpFormatter(self, room_layout: Any) -> FormattedLayout:
        """Format *room_layout* for plotting.

        At present the formatter only snaps every coordinate onto a regular
        grid; the adjusted layout is returned so callers can plot or inspect
        the result.  This supports early visualisation and will be replaced
        with the full pipeline once available.
        """

        print("Received room layout:", room_layout)
        snapped = self._snap_to_grid(room_layout)
        return snapped

    def _snap_to_grid(self, layout: Any) -> Any:
        """Return a copy of *layout* with all (x, y) points snapped to grid.

        The implementation currently expects *layout* to be a sequence of
        polygons, where each polygon is itself a sequence of ``(x, y)`` pairs.
        Coordinates are rounded to the nearest multiple of ``self._snap_precision``.
        Any unexpected structure is returned unchanged to keep the helper
        forgiving during early development.
        """

        if layout is None:
            return layout

        def snap_point(pt: Any) -> Any:
            if (
                isinstance(pt, (list, tuple))
                and len(pt) == 2
                and all(isinstance(v, (int, float)) for v in pt)
            ):
                x, y = pt
                g = self._snap_precision
                return (round(x / g) * g, round(y / g) * g)
            return pt

        # try to walk two levels deep (polygons -> points); fall back gracefully
        try:
            return [
                [snap_point(p) for p in poly]
                for poly in layout  # type: ignore
            ]
        except Exception:
            return layout
