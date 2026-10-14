from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import PROJECT_ROOT, settings


def resolve_database_url(database_url: str) -> URL:
    """Resolve relative SQLite files from the repository, not the shell CWD."""
    url = make_url(database_url)
    if (
        url.get_backend_name() != "sqlite"
        or not url.database
        or url.database == ":memory:"
        or url.query.get("uri", "").lower() in {"true", "1"}
    ):
        return url

    database_path = Path(url.database)
    if not database_path.is_absolute():
        url = url.set(database=str((PROJECT_ROOT / database_path).resolve()))
    return url


database_url = resolve_database_url(settings.DATABASE_URL)

# Determine if SQLite is used to set specific configuration args
is_sqlite = database_url.get_backend_name() == "sqlite"
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator:
    """FastAPI Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def transactional_session() -> Generator:
    """Context manager for operations that require a transaction."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
