"""
Discord database connection and session management.

This module handles the connection to the Discord data database
where the bot stores all the collected Discord activity data.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session
from app.config import settings


# Create Discord database engine
discord_engine = create_engine(
    settings.discord_database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    echo=settings.debug
)

# Create session factory
DiscordSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=discord_engine,
    class_=Session
)
