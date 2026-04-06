"""
GraphQL context setup.

Provides context data for GraphQL resolvers including database sessions,
authenticated user information, and request details.
"""

import logging
from typing import Optional
from fastapi import Request
from sqlmodel import Session
from strawberry.extensions import SchemaExtension
from strawberry.fastapi import BaseContext

from app.auth.models import ApiKey
from app.auth.dependencies import get_current_api_key
from app.auth.database import AuthSessionLocal
from app.discord.database import DiscordSessionLocal

logger = logging.getLogger(__name__)


class GraphQLContext(BaseContext):
    """
    GraphQL execution context.

    Contains all the data that GraphQL resolvers need to execute queries,
    including database sessions, authenticated user, and request information.
    """

    def __init__(
        self,
        request: Request,
        api_key: Optional[ApiKey] = None,
        auth_db: Optional[Session] = None,
        discord_db: Optional[Session] = None
    ):
        self.request = request
        self.api_key = api_key
        self.auth_db = auth_db
        self.discord_db = discord_db

    @property
    def is_authenticated(self) -> bool:
        """Check if request is authenticated."""
        return self.api_key is not None

    @property
    def is_admin(self) -> bool:
        """Check if authenticated key has admin privileges."""
        return self.api_key is not None and self.api_key.role == "admin"

    @property
    def user(self) -> Optional[ApiKey]:
        """Legacy property for compatibility."""
        return self.api_key


class DBSessionCleanupExtension(SchemaExtension):
    """Closes database sessions stored on the GraphQL context after each request."""

    def on_request_end(self):
        context = self.execution_context.context
        for attr in ("auth_db", "discord_db"):
            db = getattr(context, attr, None)
            if db is not None:
                try:
                    db.close()
                    logger.debug("Closed %s session via extension cleanup", attr)
                except Exception:
                    logger.warning("Failed to close %s session", attr, exc_info=True)


async def get_graphql_context(request: Request) -> GraphQLContext:
    """
    Create GraphQL context for each request.

    Sessions created here are guaranteed to be closed by
    DBSessionCleanupExtension.on_request_end after the request completes.
    """
    auth_db = AuthSessionLocal()
    discord_db = DiscordSessionLocal()

    try:
        api_key = await get_current_api_key(request, auth_db)
        logger.debug(f"GraphQL request authenticated with API key: {api_key.name}")
    except Exception as e:
        logger.debug(f"GraphQL request without authentication: {str(e)}")
        api_key = None

    return GraphQLContext(
        request=request,
        api_key=api_key,
        auth_db=auth_db,
        discord_db=discord_db
    )
