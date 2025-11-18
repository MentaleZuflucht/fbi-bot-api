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

    This is typically called during application startup.
    """
    try:
        logger.info("Creating auth database tables...")
        from app.auth.models import SQLModel
        SQLModel.metadata.create_all(bind=auth_engine)
        logger.info("Auth database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create auth database tables: {e}", exc_info=True)
        raise


def init_default_admin_key():
    """
    Create a default admin API key if no keys exist in the database.

    This solves the bootstrap problem: you need an admin key to create keys.
    The key is logged once on first startup so you can retrieve it from logs.

    Returns:
        tuple: (created: bool, api_key: str or None) - Whether a key was created and the key itself
    """
    from app.auth.models import ApiKey
    from sqlmodel import select

    db = AuthSessionLocal()
    try:
        # Check if any API keys exist
        existing_keys = db.exec(select(ApiKey)).first()

        if existing_keys:
            logger.info("API keys already exist, skipping default admin key creation")
            return False, None

        # No keys exist, create the first admin key
        logger.info("=" * 80)
        logger.info("🔑 No API keys found - creating initial admin key...")
        logger.info("=" * 80)

        api_key_plain, key_hash = ApiKey.generate_key()
        key_prefix = ApiKey.extract_key_prefix(api_key_plain)

        admin_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Initial Admin Key",
            role="admin"
        )

        db.add(admin_key)
        db.commit()
        db.refresh(admin_key)

        logger.info("=" * 80)
        logger.info(f"API KEY: {api_key_plain}")
        logger.info("=" * 80)

        return True, api_key_plain

    except Exception as e:
        logger.error(f"Failed to create default admin key: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
