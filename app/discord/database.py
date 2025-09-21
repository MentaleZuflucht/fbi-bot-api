"""
Discord database connection and session management.

This module handles the connection to the Discord data database
where the bot stores all the collected Discord activity data.
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session
from app.config import settings

logger = logging.getLogger(__name__)


# Create Discord database engine
discord_engine = create_engine(
    settings.discord_database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug
)

# Create session factory
DiscordSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=discord_engine,
    class_=Session
)


def get_discord_db() -> Session:
    """
    Dependency to get Discord database session.
    """
    db = DiscordSessionLocal()
    try:
        logger.debug("Created Discord database session")
        yield db
    except Exception as e:
        logger.error(f"Error in Discord database session: {e}", exc_info=True)
        raise
    finally:
        db.close()
        logger.debug("Closed Discord database session")
