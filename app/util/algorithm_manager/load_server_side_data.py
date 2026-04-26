from typing import Any, Sequence

from sqlmodel import Session

from app.core.database import engine
from app.crud import (
    room_relations_constraint as room_relations_constraint_crud,
    room_setup_template as room_setup_template_crud,
    room_size_constraint as room_size_constraint_crud,
)
from app.util.dev_use_mock_db import (
    load_room_relations_constraints,
    load_room_setup_templates,
    load_room_size_constraints,
)

# Import the Pydantic type definitions with aliases to avoid naming conflicts with CRUD modules
from app.types.room_relations_constraint import (
    RoomRelationsConstraint as RoomRelationsType,
)
from app.types.room_setup_template import RoomSetupTemplate as RoomSetupType
from app.types.room_size_constraint import RoomSizeConstraint as RoomSizeType


def load_server_side_data(
    should_bypass: bool = False,
) -> tuple[list[RoomSetupType], list[RoomSizeType], list[RoomRelationsType]]:
    """Load templates, size constraints and relation constraints from server side source.

    During development this mirrors existing manager behavior by using mock JSON data.
    The results are converted to Pydantic types for consistent downstream usage.
    """

    if should_bypass:
        print("\n\n ########## Bypass Data = TRUE ########## \n\n")
        templates = load_room_setup_templates()
        size_constraints = load_room_size_constraints()
        relation_constraints = load_room_relations_constraints()
    else:
        with Session(engine) as session:
            templates = room_setup_template_crud.get_all(session)
            size_constraints = room_size_constraint_crud.get_all(session)
            relation_constraints = room_relations_constraint_crud.get_all(session)

    return _convert_to_types(templates, size_constraints, relation_constraints)


def _convert_to_types(
    templates: Sequence[Any],
    size_constraints: Sequence[Any],
    relation_constraints: Sequence[Any],
) -> tuple[list[RoomSetupType], list[RoomSizeType], list[RoomRelationsType]]:
    """
    Private helper to convert SQLModel objects or raw dictionaries
    into formal Pydantic data types.
    """

    # Helper to handle both SQLModel objects (.model_dump()) and raw dicts
    def to_dict(obj: Any) -> dict[str, Any]:
        return obj if isinstance(obj, dict) else obj.model_dump()

    typed_templates = [RoomSetupType(**to_dict(t)) for t in templates]
    typed_sizes = [RoomSizeType(**to_dict(s)) for s in size_constraints]
    typed_relations = [RoomRelationsType(**to_dict(r)) for r in relation_constraints]

    return typed_templates, typed_sizes, typed_relations
