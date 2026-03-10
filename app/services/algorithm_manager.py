from typing import List, Tuple

from app.algorithms.floor_plan_generator import FloorPlanGenerator
from app.algorithms.floor_plan_generator.types.room import (
    RoomData,
    ConfigData,
    FpgRequirements,
)
from app.algorithms.floor_plan_generator.config import (
    FLOOR_WIDTH,
    FLOOR_HEIGHT,
    MIN_COVERAGE,
)

from sqlmodel import Session
from app.core.database import engine
from app.crud import (
    room_size_constraint as room_size_constraint_crud,
    room_setup_template as room_setup_template_crud,
)
from typing import Optional


def room_dimensions(rooms: List[RoomData], session: Session) -> List[RoomData]:
    """Normalise a list of :class:`RoomData` using database constraints.

    For each item in ``rooms`` we look up a matching
    :class:`RoomSizeConstraint` (by ``type``).  If found, the dimensions are
    pulled from the record; otherwise a set of permissive defaults is
    applied.  This mirrors the much earlier helper that used hard‑coded
    values, but now honours whatever the database contains.

    ``session`` is expected to be an open SQLModel session.  The helper does
    not close the session itself so callers retain control over transactions.
    """
    db_constraints = room_size_constraint_crud.get_all(session)
    by_type = {c.type: c for c in db_constraints}

    normalized: List[RoomData] = []
    for r in rooms:
        c = by_type.get(r.type)
        if c:
            normalized.append(
                RoomData(
                    r.name,
                    r.type,
                    min_w=int(c.min_w) if c.min_w is not None else 0,
                    min_h=int(c.min_h) if c.min_h is not None else 0,
                    max_w=int(c.max_w) if c.max_w is not None else 100,
                    max_h=int(c.max_h) if c.max_h is not None else 100,
                )
            )
        else:
            # no matching DB entry; fall back to generic bounds
            normalized.append(
                RoomData(r.name, r.type, min_w=0, min_h=0, max_w=100, max_h=100)
            )
    return normalized


def run_fpg(
    width: float = FLOOR_WIDTH,
    height: float = FLOOR_HEIGHT,
    rooms_data: List[RoomData] | None = None,
) -> tuple[List[List[Tuple[float, float]]], "FloorPlanGenerator"]:
    """Run the floor‑plan generator and return raw results (plus generator).

    The plotting side‑effect has been removed; callers receive a list of
    room polygons containing the final layout along with the underlying
    :class:`FloorPlanGenerator` instance.  The additional return value is
    useful for callers that need access to the solver and room objects
    (for example when using :meth:`PolygonPlotter.floor_plan_plot`).

    Args:
        width: floor plan width
        height: floor plan height
        rooms_data: room specs as RoomData objects; if ``None`` the
            hardcoded defaults (four generic rooms) are used.

    Returns:
        A tuple ``(polygons, generator)`` where ``polygons`` is a list of
        polygons (one per room) representing the solution.  If no solution
        was found the polygon list will be empty; the generator is returned
        regardless so callers can examine its state.
    """
    print("running floor plan generator")

    # sanitise any user-supplied room data against DB constraints
    if rooms_data is not None:
        with Session(engine) as session:
            rooms_data = room_dimensions(rooms_data, session)

    # static defaults used when no explicit rooms_data is provided
    default_rooms: List[RoomData] = [
        RoomData("livingRoom1", "livingRoom", min_w=0, min_h=0, max_w=100, max_h=100),
        RoomData("bedroom1", "bedroom", min_w=0, min_h=0, max_w=100, max_h=100),
        RoomData("bathroom1", "bathroom", min_w=0, min_h=0, max_w=100, max_h=100),
        RoomData("kitchen1", "kitchen", min_w=0, min_h=0, max_w=100, max_h=100),
    ]

    config_obj = ConfigData(
        min_coverage=MIN_COVERAGE,
        max_aspect_ratio=16.0,
        min_aspect_ratio=0.0,
        floor_plan_width=width,
        floor_plan_height=height,
    )
    requirements = FpgRequirements(
        rooms=rooms_data if rooms_data is not None else default_rooms,
        config=config_obj,
    )

    generator = FloorPlanGenerator(requirements)
    solved = generator.generate()
    if not solved:
        # still return generator so callers can inspect why it failed if
        # they wish (e.g. examine solver status, rooms, etc.)
        return [], generator

    solution = generator.get_solution()

    polygons: List[List[Tuple[float, float]]] = []
    for r in solution:
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        polygons.append([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])

    # previous versions plotted results; we now simply return the
    # computed polygons for further processing along with the generator.
    return polygons, generator


def testRunWithDBData() -> tuple[
    List[List[Tuple[float, float]]], Optional["FloorPlanGenerator"]
]:
    """Run the floor planner using the first template row from the database.

    The single record returned by :func:`app.crud.room_setup_template.get_first`
    contains a JSON ``data`` payload describing one or more rooms.  We map
    that structure into a list of :class:`RoomData` objects with permissive
    default bounds and hand the result to :func:`run_fpg`.  The generated
    polygons plus the underlying :class:`FloorPlanGenerator` instance are
    returned so that callers can either inspect the raw layout or use the
    solver/room objects for plotting or further analysis.  When the database
    contains no template the polygon list will be empty and the generator
    value will be ``None``.
    """

    with Session(engine) as session:
        template = room_setup_template_crud.get_first(session)
        if not template or not template.data:
            # nothing available in the database; short‑circuit to an empty result
            # return ``None`` for the generator so callers can detect absence
            return [], None

        # convert stored room definitions into RoomData instances; the
        # database entries generally only specify an ``id``/``name`` and a
        # ``type`` so we supply sensible defaults for the dimensional bounds.
        rooms: List[RoomData] = []
        for entry in template.data:
            name = entry.get("id") or entry.get("name") or ""
            rooms.append(
                RoomData(
                    name=name,
                    type=entry.get("type", ""),
                    min_w=0,
                    min_h=0,
                    max_w=100,
                    max_h=100,
                )
            )

    # delegate to the existing generator helper
    polygons, generator = run_fpg(rooms_data=rooms)
    return polygons, generator
