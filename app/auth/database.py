"""
Auth database connection and session management.

This module handles the connection to the separate authentication database
where API users, keys, and audit logs are stored.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from app.config import settings


# Create auth database engine
auth_engine = create_engine(
    settings.auth_database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug
)

# Create session factory
AuthSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=auth_engine,
    class_=Session
)


def get_auth_db() -> Session:
    """
    Dependency to get auth database session.

    Use this in FastAPI endpoints that need auth database access:
    """
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_auth_tables():
    """
    Create all auth tables in the database.

    This is typically called during application startup or
    through Alembic migrations.
    """
    from app.auth.models import SQLModel
    SQLModel.metadata.create_all(bind=auth_engine)
