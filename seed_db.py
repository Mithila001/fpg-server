import sys
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.database import engine
from app.util.dev_use_mock_db import (
    load_room_size_constraints,
    load_room_relations_constraints,
)
from app.schemas.db.room_size_constraints import RoomSizeConstraintCreate
from app.schemas.db.room_relations_constraints import RoomRelationsConstraintCreate
from app.crud import room_size_constraint, room_relations_constraint

def seed_database():
    with Session(engine) as session:
        # Check if already seeded
        existing_sizes = room_size_constraint.get_all(session)
        if len(existing_sizes) == 0:
            print("Seeding room_size_constraints...")
            sizes = load_room_size_constraints()
            for size_data in sizes:
                try:
                    create_data = RoomSizeConstraintCreate(**size_data.model_dump(exclude_unset=True))
                    room_size_constraint.create(session, create_data)
                except Exception as e:
                    print(f"Error inserting size constraint {size_data.type} {size_data.size}: {e}")
        else:
            print("room_size_constraints already seeded.")

        existing_relations = room_relations_constraint.get_all(session)
        if len(existing_relations) == 0:
            print("Seeding room_relations_constraints...")
            relations = load_room_relations_constraints()
            for rel_data in relations:
                try:
                    create_data = RoomRelationsConstraintCreate(**rel_data.model_dump(exclude_unset=True))
                    room_relations_constraint.create(session, create_data)
                except Exception as e:
                    print(f"Error inserting relations constraint {rel_data.room_type}: {e}")
        else:
            print("room_relations_constraints already seeded.")

if __name__ == "__main__":
    print("Starting database seeding process...")
    seed_database()
    print("Seeding complete.")
