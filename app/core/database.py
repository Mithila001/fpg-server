from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings


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
