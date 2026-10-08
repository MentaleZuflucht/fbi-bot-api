"""
GraphQL context setup.

Provides context data for GraphQL resolvers including database sessions,
authenticated user information, and request details.
"""

import logging
from typing import Optional
from fastapi import Request
from graphql import FieldNode, OperationDefinitionNode
from sqlmodel import Session, select
from strawberry.extensions import SchemaExtension
from strawberry.fastapi import BaseContext

from app.auth.models import ApiKey
from app.auth.dependencies import get_current_api_key
from app.auth.services import AuthService
from app.auth.database import AuthSessionLocal
from app.discord.database import DiscordSessionLocal
from app.discord.models import Channel

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
        self._channel_names: Optional[dict[int, str]] = None

    def channel_name(self, channel_id) -> Optional[str]:
        """Name of a channel, or None if the bot never saw it.

        The channels table is small, so it's loaded once per request instead of
        querying it for every message or voice session.
        """
        if self._channel_names is None:
            self._channel_names = dict(self.discord_db.exec(select(Channel.channel_id, Channel.name)).all())
        return self._channel_names.get(int(channel_id))

    @property
    def is_authenticated(self) -> bool:
        """Check if request is authenticated."""
        return self.api_key is not None

    @property
    def is_admin(self) -> bool:
        """Check if authenticated key has admin privileges."""
        return self.api_key is not None and self.api_key.role == "admin"


class DBSessionCleanupExtension(SchemaExtension):
    """Closes database sessions stored on the GraphQL context after each request.

    Without this the connections stay "idle in transaction", holding locks that
    block migrations, until the connection pool runs out.
    """

    def on_operation(self):
        try:
            yield
        finally:
            context = self.execution_context.context
            for attr in ("auth_db", "discord_db"):
                db = getattr(context, attr, None)
                if db is not None:
                    try:
                        db.close()
                        logger.debug("Closed %s session via extension cleanup", attr)
                    except Exception:
                        logger.warning("Failed to close %s session", attr, exc_info=True)


MAX_LIMIT = 5000


class LimitCapExtension(SchemaExtension):
    """Caps every `limit` argument, so a single query can't load millions of rows."""

    def resolve(self, _next, root, info, *args, **kwargs):
        if kwargs.get("limit") is not None:
            kwargs["limit"] = min(kwargs["limit"], MAX_LIMIT)
        return _next(root, info, *args, **kwargs)


class ApiUsageExtension(SchemaExtension):
    """Logs each request made with an API key, for the apiUsage and usageStats queries."""

    async def on_operation(self):
        yield
        context = self.execution_context.context
        api_key = getattr(context, "api_key", None)
        # The frontend logs in with a virtual key (id 0) that has no row to log against
        if not api_key or not api_key.id:
            return

        fields = []
        document = self.execution_context.graphql_document
        for definition in document.definitions if document else []:
            if isinstance(definition, OperationDefinitionNode):
                fields += [s.name.value for s in definition.selection_set.selections
                           if isinstance(s, FieldNode)]

        result = self.execution_context.result
        try:
            await AuthService.record_api_usage(
                api_key=api_key,
                endpoint=f"/graphql: {', '.join(fields)}"[:200],
                method=context.request.method,
                response_status=400 if result is None or result.errors else 200,
                db=context.auth_db,
            )
        except Exception:
            context.auth_db.rollback()
            logger.warning("Failed to log API usage", exc_info=True)


async def get_graphql_context(request: Request) -> GraphQLContext:
    """
    Create GraphQL context for each request.

    Sessions created here are guaranteed to be closed by
    DBSessionCleanupExtension after the request completes.
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
