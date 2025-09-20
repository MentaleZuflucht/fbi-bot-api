"""
GraphQL context setup.

Provides context data for GraphQL resolvers including database sessions,
authenticated user information, and request details.
"""

import logging
from typing import Optional
from fastapi import Request
from sqlmodel import Session
from strawberry.fastapi import BaseContext

from app.auth.models import ApiKey
from app.auth.dependencies import get_current_api_key
from app.auth.database import get_auth_db
from app.discord.database import get_discord_db

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


async def get_graphql_context(request: Request) -> GraphQLContext:
    """
    Create GraphQL context for each request.

    This function is called for every GraphQL request to set up the context
    that will be available to all resolvers.

    Args:
        request: FastAPI request object

    Returns:
        GraphQLContext: Context object with database sessions and user info
    """
    # Get database sessions
    auth_db_gen = get_auth_db()
    auth_db = next(auth_db_gen)

    discord_db_gen = get_discord_db()
    discord_db = next(discord_db_gen)

    try:
        # Try to authenticate API key
        try:
            api_key = await get_current_api_key(request, auth_db)
            logger.debug(f"GraphQL request authenticated with API key: {api_key.name}")
        except Exception as e:
            logger.debug(f"GraphQL request without authentication: {str(e)}")
            api_key = None

        context = GraphQLContext(
            request=request,
            api_key=api_key,
            auth_db=auth_db,
            discord_db=discord_db
        )

        return context

    except Exception as e:
        # Clean up database sessions on error
        auth_db.close()
        discord_db.close()
        raise e
