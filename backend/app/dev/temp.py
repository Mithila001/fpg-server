# This file will delete withing today

# python app/dev/temp.py

# quick check to ensure the ORM mapping for RoomSizeConstraint works

# make sure the project root is on PYTHONPATH so `import app` works when
# running this script directly
import os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root not in sys.path:
    sys.path.insert(0, root)

if __name__ == "__main__":
    from app.models.room_size_constraint import RoomSizeConstraint
    from app.core import database
    from sqlalchemy import inspect

    print("tablename attribute:", RoomSizeConstraint.__tablename__)
    inspector = inspect(database.engine)
    print("tables present in database:", inspector.get_table_names())

