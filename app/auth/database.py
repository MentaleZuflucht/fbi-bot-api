"""
Auth database connection and session management.

This module handles the connection to the separate authentication database
where API users, keys, and audit logs are stored.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from app.config import settings

logger = logging.getLogger(__name__)


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
        logger.debug("Created auth database session")
        yield db
    except Exception as e:
        logger.error(f"Error in auth database session: {e}", exc_info=True)
        raise
    finally:
        db.close()
        logger.debug("Closed auth database session")


def create_auth_tables():
    """
    Create all auth tables in the database.

    This is typically called during application startup or
    through Alembic migrations.
    """
    try:
        logger.info("Creating auth database tables...")
        from app.auth.models import SQLModel
        SQLModel.metadata.create_all(bind=auth_engine)
        logger.info("Auth database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create auth database tables: {e}", exc_info=True)
        raise
