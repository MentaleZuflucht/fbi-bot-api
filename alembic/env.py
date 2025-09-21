from logging.config import fileConfig
import os
from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlalchemy import engine_from_config, MetaData
from sqlalchemy import pool
from alembic import context

# Import ONLY auth models for this Alembic setup
# We import them directly to avoid importing the entire app
from app.auth.models import ApiKey, ApiUsage

# Load environment variables from .env file
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the sqlalchemy.url from environment variable
# This allows us to keep the database URL in .env file instead of alembic.ini
if config.config_file_name is not None:
    # Use AUTH_DATABASE_URL for auth database migrations
    database_url = os.getenv('AUTH_DATABASE_URL')
    if database_url:
        config.set_main_option('sqlalchemy.url', database_url)
    else:
        # If AUTH_DATABASE_URL is not set, raise an error with helpful message
        raise ValueError(
            "AUTH_DATABASE_URL environment variable is not set. "
            "Please add AUTH_DATABASE_URL=your_auth_database_connection_string to your .env file"
        )

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Create metadata that only includes auth models
# Filter the global SQLModel.metadata to only include our auth tables
auth_metadata = MetaData()

# Only copy auth-related tables to our filtered metadata
for table_name, table in SQLModel.metadata.tables.items():
    if table_name in ('api_keys', 'api_usage'):
        table.tometadata(auth_metadata)

target_metadata = auth_metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
