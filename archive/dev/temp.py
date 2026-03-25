# This file will delete withing today

# python app/dev/temp.py

# Verify that all room_size_constraints rows are returned from the database.

# make sure the project root is on PYTHONPATH so `import app` works when
# running this script directly
import os, sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root not in sys.path:
    sys.path.insert(0, root)

if __name__ == "__main__":
    from sqlmodel import Session
    from app.core.database import engine, create_db_and_tables
    from app.crud.room_size_constraint import get_all

    # ensure the table exists (idempotent — skipped if already present)
    create_db_and_tables()

    with Session(engine) as session:
        records = get_all(session)

    print(f"\n\nTotal records: {len(records)}")
    for row in records:
        print(row)
