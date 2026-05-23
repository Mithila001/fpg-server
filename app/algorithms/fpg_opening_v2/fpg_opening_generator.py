from app.algorithms.types.domain import FpgRequirements, ProcessedRoomData
from app.algorithms.types.openings import FloorPlanWithOpenings, OpeningData
from app.algorithms.fpg_opening_v2.constratins.back_door_placement import (
    select_back_door,
)
from app.algorithms.fpg_opening_v2.constratins.internal_doors_placement import (
    build_internal_door_candidates,
    select_internal_doors,
)
from app.algorithms.fpg_opening_v2.constratins.main_door_to_outside import (
    select_main_door,
)
from app.algorithms.fpg_opening_v2.constratins.windows_placement import select_windows
from app.algorithms.fpg_opening_v2.dev.opening_plotter import (
    fpg_opening_results_plotter,
)


def generate_fpg_openings(
    requirements: FpgRequirements,
    floor_plan: list[ProcessedRoomData],
    side_priority: tuple[str, ...] = ("south", "east", "north", "west"),
    preferred_door_length: float = 8.0,
    window_width: float = 16.0,
    window_door_clearance: float = 5.0,
    tolerance: float = 1e-6,
) -> FloorPlanWithOpenings:
    """Main Entry for Opening Generator"""
    if not floor_plan:
        return FloorPlanWithOpenings(floor_plan=[], openings=[])

    openings: list[OpeningData] = []

    # 1) Internal doors from shared boundaries.
    internal_candidates = build_internal_door_candidates(
        floor_plan=floor_plan,
        tolerance=tolerance,
    )
    openings.extend(
        select_internal_doors(
            candidates=internal_candidates,
            preferred_door_length=preferred_door_length,
            tolerance=tolerance,
        )
    )

    # 2) Main door rule: if veranda exists, promote living<->veranda internal door.
    has_veranda = any(room.type.strip().lower() == "veranda" for room in floor_plan)
    if has_veranda:
        for opening in openings:
            pair = {
                opening.room_type.strip().lower(),
                opening.connected_room_type.strip().lower(),
            }
            if opening.opening_type == "internalDoor" and pair == {
                "livingroom",
                "veranda",
            }:
                opening.opening_type = "mainDoor"
                break
    else:
        main_door = select_main_door(
            floor_plan=floor_plan,
            side_priority=side_priority,
            preferred_door_length=preferred_door_length,
            tolerance=tolerance,
        )
        if main_door is not None:
            openings.append(main_door)

    # 3) Back door.
    back_door = select_back_door(
        floor_plan=floor_plan,
        preferred_door_length=preferred_door_length,
        existing_openings=openings,
        tolerance=tolerance,
    )
    if back_door is not None:
        openings.append(back_door)

    # 4) Windows.
    openings.extend(
        select_windows(
            floor_plan=floor_plan,
            existing_openings=openings,
            window_width=window_width,
            window_door_clearance=window_door_clearance,
            tolerance=tolerance,
        )
    )

    result = FloorPlanWithOpenings(floor_plan=floor_plan, openings=openings)

    # # Best-effort debug plot only; generation must stay functional even if plotting fails.
    # try:
    #     if openings:
    #         fpg_opening_results_plotter(
    #             requirements=requirements,
    #             floor_plan=floor_plan,
    #             openings=openings,
    #         )
    # except Exception:
    #     pass

    return result
