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


def load_server_side_data() -> tuple[list[Any], Sequence[Any], Sequence[Any]]:
    """Load templates, size constraints and relation constraints from server side source.

    During development this mirrors existing manager behavior by using mock JSON data.
    """
    should_bypass = True
    print("\n\n ########## Bypass Data = TRUE ########## \n\n")

    if should_bypass:
        templates = load_room_setup_templates()
        size_constraints = load_room_size_constraints()
        relation_constraints = load_room_relations_constraints()
        return templates, size_constraints, relation_constraints

    with Session(engine) as session:
        templates = room_setup_template_crud.get_all(session)
        size_constraints = room_size_constraint_crud.get_all(session)
        relation_constraints = room_relations_constraint_crud.get_all(session)

    return templates, size_constraints, relation_constraints
