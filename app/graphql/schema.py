"""
GraphQL schema definition.

This module creates the main GraphQL schema that combines all types and resolvers,
and sets up the FastAPI GraphQL endpoint with authentication.
"""

import logging
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import List
from datetime import datetime, timedelta
from sqlmodel import select, func
from app.graphql.context import get_graphql_context, GraphQLContext
from app.graphql.types.auth import (
    ApiKeyType, ApiUsageType, AuthStatsType, ApiKeyUsageStatsType, UserRoleType
)
from app.graphql.types.discord import (
    UserType, MessageActivityType, VoiceSessionType, ActivityLogType,
    PresenceStatusLogType, CustomStatusType, UserNameHistoryType,
    ChannelStatsType, ServerStatsType, UserStatsType,
    ActivityTypeEnum, MessageTypeEnum, DiscordStatusEnum, VoiceStateTypeEnum
)
from app.graphql.resolvers.discord import Query as DiscordQuery
from app.auth.models import ApiKey, ApiUsage

logger = logging.getLogger(__name__)


@strawberry.type
class Query(DiscordQuery):
    """
    Main GraphQL Query type.

    Combines all query resolvers from different modules.
    All queries require authentication via Bearer token.
    """

    @strawberry.field
    def hello(self, info: strawberry.Info[GraphQLContext, None]) -> str:
        """Simple hello query for testing."""
        if not info.context.is_authenticated:
            logger.debug("Unauthenticated hello query")
            return "Hello! Please authenticate to access Discord data."

        user_name = info.context.api_key.name if info.context.api_key else "Unknown"
        logger.debug(f"GraphQL hello query from {user_name}")
        return f"Hello {user_name}! You have access to the Discord data API."

    # Auth-related queries (admin only)
    @strawberry.field
    def api_keys(
        self,
        info: strawberry.Info[GraphQLContext, None]
    ) -> List[ApiKeyType]:
        """Get all API keys (admin only)."""
        if not info.context.is_admin:
            raise Exception("Admin access required")

        keys = info.context.auth_db.exec(
            select(ApiKey).order_by(ApiKey.created_at.desc())
        ).all()

        return [ApiKeyType.from_model(key) for key in keys]

    @strawberry.field
    def api_key(
        self,
        info: strawberry.Info[GraphQLContext, None],
        key_id: int
    ) -> ApiKeyType:
        """Get a specific API key by ID (admin only)."""
        if not info.context.is_admin:
            raise Exception("Admin access required")

        key = info.context.auth_db.exec(
            select(ApiKey).where(ApiKey.id == key_id)
        ).first()

        if not key:
            raise Exception("API key not found")

        return ApiKeyType.from_model(key)

    @strawberry.field
    def api_usage(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 100,
        days: int = 7
    ) -> List[ApiUsageType]:
        """Get API usage logs (admin only)."""
        if not info.context.is_admin:
            raise Exception("Admin access required")

        start_date = datetime.utcnow() - timedelta(days=days)

        usage_logs = info.context.auth_db.exec(
            select(ApiUsage, ApiKey.name)
            .join(ApiKey)
            .where(ApiUsage.timestamp >= start_date)
            .order_by(ApiUsage.timestamp.desc())
            .limit(limit)
        ).all()

        return [
            ApiUsageType.from_model(usage, api_key_name)
            for usage, api_key_name in usage_logs
        ]

    @strawberry.field
    def auth_stats(
        self,
        info: strawberry.Info[GraphQLContext, None]
    ) -> AuthStatsType:
        """Get authentication statistics (admin only)."""
        if not info.context.is_admin:
            raise Exception("Admin access required")

        # Count API keys by role
        total_keys = info.context.auth_db.exec(
            select(func.count(ApiKey.id))
        ).first() or 0

        admin_keys = info.context.auth_db.exec(
            select(func.count(ApiKey.id)).where(ApiKey.role == "admin")
        ).first() or 0

        read_keys = info.context.auth_db.exec(
            select(func.count(ApiKey.id)).where(ApiKey.role == "read")
        ).first() or 0

        # Count requests today
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        requests_today = info.context.auth_db.exec(
            select(func.count(ApiUsage.id)).where(ApiUsage.timestamp >= today)
        ).first() or 0

        return AuthStatsType(
            total_api_keys=total_keys,
            admin_keys=admin_keys,
            read_keys=read_keys,
            total_requests_today=requests_today
        )

    @strawberry.field
    def me(self, info: strawberry.Info[GraphQLContext, None]) -> ApiKeyType:
        """Get information about the current API key."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        return ApiKeyType.from_model(info.context.api_key)


# Create the GraphQL schema
schema = strawberry.Schema(
    query=Query,
    types=[
        # Auth types
        ApiKeyType, ApiUsageType, AuthStatsType, ApiKeyUsageStatsType, UserRoleType,
        # Discord types
        UserType, MessageActivityType, VoiceSessionType, ActivityLogType,
        PresenceStatusLogType, CustomStatusType, UserNameHistoryType,
        ChannelStatsType, ServerStatsType, UserStatsType,
        # Enums
        ActivityTypeEnum, MessageTypeEnum, DiscordStatusEnum, VoiceStateTypeEnum
    ]
)

# Create the FastAPI GraphQL router
graphql_app = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
    graphiql=True  # Enable GraphiQL interface
)
