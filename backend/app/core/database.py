from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

# import models so they are registered with SQLModel.metadata
# (any new model should be imported somewhere before create_all is called).
from app.models import user  # noqa: F401  <-- import for side effects only
from app.models import room_size_constraint  # noqa: F401  <- ensure table is created

# create engine using the URL from settings
engine = create_engine(settings.DB_URL, echo=True)


def create_db_and_tables() -> None:
    """Create database tables from SQLModel models.

    Called on application startup. If you prefer migrations you can
    remove this and use Alembic instead.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield a new database session for dependency injection."""
    with Session(engine) as session:
        yield session
