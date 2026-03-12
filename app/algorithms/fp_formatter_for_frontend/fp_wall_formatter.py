from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.algorithms.floor_plan_generator.generator import FloorPlanGenerator  # noqa: F401

# Type aliases
WallSegment = Tuple[Tuple[float, float], Tuple[float, float]]
CollinearLine = List[Tuple[float, float]]  # ordered sequence of points on one axis line
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
        segmented = self._split_segments_by_orientation(room_layout)
        # once segments are classified by room we can further coalesce them
        # across the entire layout by their axis alignment.
        horiz_groups, vert_groups = self._group_segments_by_axis(segmented)
        self._merged_horiz, self._merged_vert = self._merge_collinear_segments(
            horiz_groups, vert_groups
        )

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

    # ── Step 2 ──────────────────────────────────────────────────────────────

    def _split_segments_by_orientation(
        self, room_layout: Any
    ) -> Dict[str, Dict[str, List[WallSegment]]]:
        """Split each room's wall segments into horizontal and vertical groups.

        The formatter may receive *room_layout* in one of two forms:

        1. A list of dictionaries describing each room (the output of
           ``FloorPlanGenerator.get_solution``).  In this case we derive the
           four edges of the axis-aligned rectangle using the ``x``/``y``
           coordinates and their ``_end`` counterparts.

        2. A list of polygons, where each room is represented by a sequence of
           ``(x, y)`` points.  This is the format produced by the planner when
           polygons are returned directly (as seen in ``debug_fp_formatter``).
           Here we iterate consecutive point pairs (closing the loop) to build
           the wall segments.

        Segments whose endpoints share an identical *y* value are classified as
        **horizontal**; those sharing an identical *x* value are treated as
        **vertical**.  Any irregular segments (neither purely horizontal nor
        vertical) are ignored to keep the output simple.

        The return value is a mapping from room identifier to the two segment
        groups:

        ``{ name: {"horizontal": [...], "vertical": [...]} }``
        """
        result: Dict[str, Dict[str, List[WallSegment]]] = {}

        for idx, room in enumerate(room_layout or []):
            # determine whether we have a dict or a polygon-like list
            horizontal: List[WallSegment] = []
            vertical: List[WallSegment] = []

            if isinstance(room, dict):
                name: str = room.get("name", f"room_{idx}")
                x: float = room["x"]
                y: float = room["y"]
                x_end: float = room["x_end"]
                y_end: float = room["y_end"]

                all_segments: List[WallSegment] = [
                    ((x, y), (x_end, y)),
                    ((x, y_end), (x_end, y_end)),
                    ((x, y), (x, y_end)),
                    ((x_end, y), (x_end, y_end)),
                ]
            elif isinstance(room, (list, tuple)):
                name = f"room_{idx}"
                pts = room  # type: ignore[var-annotated]
                all_segments = []
                if len(pts) >= 2:
                    for i in range(len(pts)):
                        p1 = pts[i]
                        p2 = pts[(i + 1) % len(pts)]
                        # ensure we have numeric pairs
                        if (
                            isinstance(p1, (list, tuple))
                            and isinstance(p2, (list, tuple))
                            and len(p1) == 2
                            and len(p2) == 2
                        ):
                            all_segments.append(((float(p1[0]), float(p1[1])),
                                                 (float(p2[0]), float(p2[1]))))
            else:
                # unknown room format; skip but log for debugging
                print(f"Skipping unsupported room type: {type(room)}")
                continue

            for seg in all_segments:
                (x1, y1), (x2, y2) = seg
                if y1 == y2:
                    horizontal.append(seg)
                elif x1 == x2:
                    vertical.append(seg)

            result[name] = {"horizontal": horizontal, "vertical": vertical}

            # print(f"Room: {name}")
            # print(f"  Horizontal segments ({len(horizontal)}):")
            # for seg in horizontal:
            #     print(f"    {seg[0]} --> {seg[1]}")
            # print(f"  Vertical segments ({len(vertical)}):")
            # for seg in vertical:
            #     print(f"    {seg[0]} --> {seg[1]}")

        return result

    def _group_segments_by_axis(
        self,
        segmented: Dict[str, Dict[str, List[WallSegment]]],
    ) -> Tuple[Dict[float, List[WallSegment]], Dict[float, List[WallSegment]]]:
        """Aggregate horizontal/vertical segments by their constant axis.

        *segmented* is the dictionary returned by
        :meth:`_split_segments_by_orientation`.  We iterate over every room's
        segments, collecting all horizontal segments into a map keyed by their
        *y* coordinate and all vertical segments keyed by their *x* coordinate.

        The method prints a summary suitable for human inspection and returns a
        tuple ``(horiz_groups, vert_groups)`` where each group map has floats as
        keys and lists of wall segments as values.
        """
        horiz_groups: Dict[float, List[WallSegment]] = {}
        vert_groups: Dict[float, List[WallSegment]] = {}

        for name, groups in segmented.items():
            for seg in groups.get("horizontal", []):
                # horizontal segment has equal y for both endpoints
                y = seg[0][1]
                horiz_groups.setdefault(y, []).append(seg)
            for seg in groups.get("vertical", []):
                x = seg[0][0]
                vert_groups.setdefault(x, []).append(seg)

        # printing the aggregated result
        print("\nGrouped horizontal segments by y:")
        for y, segs in sorted(horiz_groups.items()):
            print(f" y={y}: {len(segs)} segments")
            for s in segs:
                print(f"   {s[0]} --> {s[1]}")

        print("\nGrouped vertical segments by x:")
        for x, segs in sorted(vert_groups.items()):
            print(f" x={x}: {len(segs)} segments")
            for s in segs:
                print(f"   {s[0]} --> {s[1]}")

        return horiz_groups, vert_groups

    # ── Step 3 ──────────────────────────────────────────────────────────────

    def _merge_collinear_segments(
        self,
        horiz_groups: Dict[float, List[WallSegment]],
        vert_groups: Dict[float, List[WallSegment]],
    ) -> Tuple[Dict[float, List[CollinearLine]], Dict[float, List[CollinearLine]]]:
        """Merge connected segments into collinear polylines, keeping all points.

        For each axis value the input segments are interval-merged.  When
        segments are adjacent or overlapping, **all** unique endpoint
        coordinates are collected, de-duplicated, and sorted — producing one
        :data:`CollinearLine` (an ordered sequence of collinear points) that
        spans the full extent while still exposing every intermediate point.
        Disconnected groups on the same axis line produce separate collinear
        lines.  Single-segment entries pass through the same path so the
        return structure is always uniform.

        Returns ``(merged_horiz, merged_vert)`` where each value is a list of
        :data:`CollinearLine` instances.
        """

        def _merge_horiz(segs: List[WallSegment], y_val: float) -> List[CollinearLine]:
            # build (lo, hi, {all x coords}) per segment, sorted by lo
            items = sorted(
                [
                    (min(s[0][0], s[1][0]), max(s[0][0], s[1][0]), {s[0][0], s[1][0]})
                    for s in segs
                ],
                key=lambda t: t[0],
            )
            result: List[CollinearLine] = []
            cur_lo, cur_hi, cur_xs = items[0]
            for lo, hi, xs in items[1:]:
                if lo <= cur_hi:          # touching or overlapping → extend
                    cur_hi = max(cur_hi, hi)
                    cur_xs = cur_xs | xs
                else:                     # gap → flush current group
                    result.append([(xv, y_val) for xv in sorted(cur_xs)])
                    _, cur_hi, cur_xs = lo, hi, xs
            result.append([(xv, y_val) for xv in sorted(cur_xs)])
            return result

        def _merge_vert(segs: List[WallSegment], x_val: float) -> List[CollinearLine]:
            items = sorted(
                [
                    (min(s[0][1], s[1][1]), max(s[0][1], s[1][1]), {s[0][1], s[1][1]})
                    for s in segs
                ],
                key=lambda t: t[0],
            )
            result: List[CollinearLine] = []
            cur_lo, cur_hi, cur_ys = items[0]
            for lo, hi, ys in items[1:]:
                if lo <= cur_hi:
                    cur_hi = max(cur_hi, hi)
                    cur_ys = cur_ys | ys
                else:
                    result.append([(x_val, yv) for yv in sorted(cur_ys)])
                    _, cur_hi, cur_ys = lo, hi, ys
            result.append([(x_val, yv) for yv in sorted(cur_ys)])
            return result

        merged_horiz: Dict[float, List[CollinearLine]] = {}
        merged_vert: Dict[float, List[CollinearLine]] = {}

        for y, segs in sorted(horiz_groups.items()):
            merged_horiz[y] = _merge_horiz(segs, y)

        for x, segs in sorted(vert_groups.items()):
            merged_vert[x] = _merge_vert(segs, x)

        print("\nMerged horizontal segments:")
        for y, lines in sorted(merged_horiz.items()):
            print(f"  y={y}: {len(lines)} line(s)")
            for line in lines:
                print("    " + " --> ".join(str(pt) for pt in line))

        print("\nMerged vertical segments:")
        for x, lines in sorted(merged_vert.items()):
            print(f"  x={x}: {len(lines)} line(s)")
            for line in lines:
                print("    " + " --> ".join(str(pt) for pt in line))

        return merged_horiz, merged_vert
    
