from app.algorithms.fpg_rooms.types.room import RoomData
from app.core.fpg_rooms.config_fpg import (
    DEFAULT_MAX_H,
    DEFAULT_MAX_W,
    DEFAULT_MIN_H,
    DEFAULT_MIN_W,
)
from app.schemas.db.room_setup_template import RoomSetupTemplateBase


def build_rooms_from_template(template: RoomSetupTemplateBase) -> list[RoomData]:
    rooms: list[RoomData] = []
    for entry in template.data:
        room_type = entry.get("type", "")
        room_name = entry.get("name") or entry.get("id") or room_type
        rooms.append(
            RoomData(
                name=room_name,
                type=room_type,
                min_w=DEFAULT_MIN_W,
                min_h=DEFAULT_MIN_H,
                max_w=DEFAULT_MAX_W,
                max_h=DEFAULT_MAX_H,
            )
        )
    return rooms
