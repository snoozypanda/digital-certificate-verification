"""
Database configuration module.

Sets up SQLAlchemy engine, session factory, and declarative base.
Provides a dependency function for FastAPI route injection.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Create the SQLAlchemy engine
# Supports SQLite fallback if PostgreSQL is not available
db_url = settings.database_url

try:
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        engine = create_engine(
            db_url,
            connect_args=connect_args,
            echo=False,
        )
    else:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )
        # Test connection
        with engine.connect() as conn:
            pass
except Exception as e:
    logger.warning(
        f"Failed to connect to primary database ({db_url}): {e}. "
        "Falling back to local SQLite database 'certificates.db'."
    )
    db_url = "sqlite:///./certificates.db"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

# Session factory — each call creates a new session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    Yields a session and ensures it is closed after the request,
    even if an exception occurs.

    Usage in routes:
        @router.get("/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
