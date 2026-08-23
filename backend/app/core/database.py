"""SQLAlchemy database engine, session factory and declarative base.

The design is SQLite-friendly for local development and PostgreSQL-compatible
for production (no SQLite-only column types are used).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _create_engine(database_url: str):
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
    return create_engine(database_url, pool_pre_ping=True)


settings = get_settings()
engine = _create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables for the configured database.

    Alembic migrations are the canonical way to evolve the schema in
    production; this helper guarantees a working schema in development and
    in fresh deployments without extra steps.
    """
    # Import models so they are registered on Base.metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
