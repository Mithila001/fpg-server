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
    """Helper for preparing floor‑plan layouts for frontend tools.

    The formatter currently performs simple grid snapping, orientation
    categorisation and collinear merging of wall segments.  It exists as an
    interim step until a full layout pipeline is available.
    """

    def __init__(self, snap_precision: float = 0.1) -> None:
        """Initialise with a grid resolution.

        ``snap_precision`` defines the spacing used when snapping coordinates to
        the grid in :meth:`_snap_to_grid`.
        """
        self._snap_precision = snap_precision

    # Main Entry Function
    def fpFormatter(self, room_layout: Any) -> FormattedLayout:
        """Primary entry point used by clients.

        The input may be a list of room dictionaries (from
        :class:`FloorPlanGenerator`) or raw polygons.  The routine snaps
        coordinates, splits walls into horizontal/vertical segments, groups
        them by their constant axis, and finally merges any collinear pieces
        into ordered point sequences.  The return value is a pair of mappings
        describing the merged horizontal and vertical lines.
        """
        snapped = self._snap_to_grid(room_layout)
        segmented = self._split_segments_by_orientation(snapped)
        # classify segments by axis before merging across rooms
        horiz_groups, vert_groups = self._group_segments_by_axis(segmented)
        merged_horiz, merged_vert = self._merge_collinear_segments(
            horiz_groups, vert_groups
        )

        return merged_horiz, merged_vert

    def _snap_to_grid(self, layout: Any) -> Any:
        """Round every coordinate in *layout* to the nearest grid point.

        Works on a list of polygons (lists of ``(x, y)`` tuples).  If the input
        does not conform, the original value is returned unchanged.
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

        # attempt a two‑level traversal; if layout is not iterable in the
        # expected way just return it unchanged rather than raising.
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
        """Break each room into its horizontal and vertical wall segments.

        Input may be a list of room dictionaries (with ``x``, ``y`` and
        ``_end`` keys) or polygons (sequence of points).  For dictionary
        entries the four sides of the rectangle are constructed; for polygons
        we walk each edge in turn.

        Only perfectly axis-aligned segments are kept.  The result is a map
        from room name to two lists under the keys ``"horizontal"`` and
        ``"vertical"``.
        """
        result: Dict[str, Dict[str, List[WallSegment]]] = {}

        for idx, room in enumerate(room_layout or []):
            # prepare containers for this room
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
                        # only add well-formed numeric pairs
                        if (
                            isinstance(p1, (list, tuple))
                            and isinstance(p2, (list, tuple))
                            and len(p1) == 2
                            and len(p2) == 2
                        ):
                            all_segments.append(
                                (
                                    (float(p1[0]), float(p1[1])),
                                    (float(p2[0]), float(p2[1])),
                                )
                            )
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

        return result

    def _group_segments_by_axis(
        self,
        segmented: Dict[str, Dict[str, List[WallSegment]]],
    ) -> Tuple[Dict[float, List[WallSegment]], Dict[float, List[WallSegment]]]:
        """Collect segments sharing the same axis value.

        Walk the output of :meth:`_split_segments_by_orientation` and build two
        dictionaries: horizontal segments grouped by their constant ``y`` and
        vertical ones by ``x``.  Useful for downstream merging.
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

        # # debug dump of grouped segments
        # print("\nGrouped horizontal segments by y:")
        # for y, segs in sorted(horiz_groups.items()):
        #     print(f" y={y}: {len(segs)} segments")
        #     for s in segs:
        #         print(f"   {s[0]} --> {s[1]}")

        # print("\nGrouped vertical segments by x:")
        # for x, segs in sorted(vert_groups.items()):
        #     print(f" x={x}: {len(segs)} segments")
        #     for s in segs:
        #         print(f"   {s[0]} --> {s[1]}")

        return horiz_groups, vert_groups

    # ── Step 3 ──────────────────────────────────────────────────────────────

    def _merge_collinear_segments(
        self,
        horiz_groups: Dict[float, List[WallSegment]],
        vert_groups: Dict[float, List[WallSegment]],
    ) -> Tuple[Dict[float, List[CollinearLine]], Dict[float, List[CollinearLine]]]:
        """Combine overlapping or adjacent wall segments along the same line.

        Each group is reduced so that touching/overlapping segments yield a
        single ordered sequence of unique points.  Separate clusters on a
        common axis remain as distinct polylines.  The structure of the return
        value mirrors the input: dictionaries keyed by axis values with lists
        of collinear point sequences.
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
                if lo <= cur_hi:  # touching or overlapping → extend
                    cur_hi = max(cur_hi, hi)
                    cur_xs = cur_xs | xs
                else:  # gap → flush current group
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

        # print("\nMerged horizontal segments:")
        # for y, lines in sorted(merged_horiz.items()):
        #     print(f"  y={y}: {len(lines)} line(s)")
        #     for line in lines:
        #         print("    " + " --> ".join(str(pt) for pt in line))

        # print("\nMerged vertical segments:")
        # for x, lines in sorted(merged_vert.items()):
        #     print(f"  x={x}: {len(lines)} line(s)")
        #     for line in lines:
        #         print("    " + " --> ".join(str(pt) for pt in line))

        return merged_horiz, merged_vert
