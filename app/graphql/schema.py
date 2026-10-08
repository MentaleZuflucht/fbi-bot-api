"""
GraphQL schema definition.

This module creates the main GraphQL schema that combines all types and resolvers,
and sets up the FastAPI GraphQL endpoint with authentication.
"""

import logging
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import Annotated, List
from datetime import datetime, timedelta
from sqlmodel import select, func
from app.graphql.arguments import Limit
from app.graphql.context import (
    get_graphql_context, GraphQLContext, DBSessionCleanupExtension, LimitCapExtension
)
from app.graphql.types.auth import (
    ApiKeyType, ApiUsageType, AuthStatsType, ApiKeyUsageStatsType, UserRoleType,
    CreateApiKeyResult
)
from app.graphql.types.discord import (
    UserType, MessageActivityType, VoiceSessionType, ActivityLogType,
    PresenceStatusLogType, CustomStatusType, UserNameHistoryType,
    ChannelStatsType, ServerStatsType, UserStatsType,
    DailyStatsType, HourlyDistributionType, TopItemType, TopUserType,
    TopVoiceStateUserType, UniqueActivityType, VoiceConnectionType,
    ActivityTypeEnum, MessageTypeEnum, DiscordStatusEnum, VoiceStateTypeEnum
)
from app.graphql.resolvers.discord import Query as DiscordQuery
from app.auth.models import ApiKey, ApiUsage
from app.auth.services import AuthService

logger = logging.getLogger(__name__)


@strawberry.type(description="""Discord server activity collected by the FBI Bot.

Every request needs your API key as a header: `{"Authorization": "Bearer sk_live_..."}` \
(in GraphiQL: the Headers tab below the query editor). Try `hello` to check that your key works.

- IDs are strings, because Discord IDs are too big for GraphQL's Int.
- All times are UTC.
- Durations in hours are rounded to 2 decimals.
- Date filters: use `days` for "the last N days", or `startDate`/`endDate` for a fixed range.""")
class Query(DiscordQuery):
    @strawberry.field(
        description="Says hello with the name of your API key. Handy to check that your key works."
    )
    def hello(self, info: strawberry.Info[GraphQLContext, None]) -> str:
        if not info.context.is_authenticated:
            logger.debug("Unauthenticated hello query")
            return "Hello! Please authenticate to access Discord data."

        user_name = info.context.api_key.name if info.context.api_key else "Unknown"
        logger.debug(f"GraphQL hello query from {user_name}")
        return f"Hello {user_name}! You have access to the Discord data API."

    # Auth-related queries (admin only)
    @strawberry.field(description="All API keys, newest first. Admin only.")
    def api_keys(
        self,
        info: strawberry.Info[GraphQLContext, None]
    ) -> List[ApiKeyType]:
        if not info.context.is_admin:
            raise Exception("Admin access required")

        keys = info.context.auth_db.exec(
            select(ApiKey).order_by(ApiKey.created_at.desc())
        ).all()

        return [ApiKeyType.from_model(key) for key in keys]

    @strawberry.field(description="One API key by its ID. Admin only.")
    def api_key(
        self,
        info: strawberry.Info[GraphQLContext, None],
        key_id: int
    ) -> ApiKeyType:
        if not info.context.is_admin:
            raise Exception("Admin access required")

        key = info.context.auth_db.exec(
            select(ApiKey).where(ApiKey.id == key_id)
        ).first()

        if not key:
            raise Exception("API key not found")

        return ApiKeyType.from_model(key)

    @strawberry.field(description="API request log, newest first. Admin only.")
    def api_usage(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 100,
        days: Annotated[int, strawberry.argument(description="Look back this many days.")] = 7
    ) -> List[ApiUsageType]:
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

    @strawberry.field(description="Number of API keys and requests today. Admin only.")
    def auth_stats(
        self,
        info: strawberry.Info[GraphQLContext, None]
    ) -> AuthStatsType:
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

    @strawberry.field(description="The API key you are using.")
    def me(self, info: strawberry.Info[GraphQLContext, None]) -> ApiKeyType:
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        return ApiKeyType.from_model(info.context.api_key)


@strawberry.type(description="Managing API keys. Admin only.")
class Mutation:
    @strawberry.mutation(description=(
        "Create an API key, e.g. for a friend. "
        "The full key is only shown here, once, so save it. Admin only."
    ))
    async def create_api_key(
        self,
        info: strawberry.Info[GraphQLContext, None],
        name: Annotated[str, strawberry.argument(description='Who the key is for, e.g. "Alice".')],
        role: Annotated[UserRoleType, strawberry.argument(
            description="READ can query data, ADMIN can also manage keys."
        )] = UserRoleType.READ
    ) -> CreateApiKeyResult:
        if not info.context.is_admin:
            raise Exception("Admin access required")

        api_key_obj, plain_key = await AuthService.create_api_key(
            name=name,
            role=role.value,
            db=info.context.auth_db
        )

        logger.info(f"Admin '{info.context.api_key.name}' created API key '{name}' via GraphQL")

        return CreateApiKeyResult(
            id=api_key_obj.id,
            name=api_key_obj.name,
            key_prefix=api_key_obj.key_prefix,
            role=UserRoleType(api_key_obj.role.value),
            created_at=api_key_obj.created_at,
            api_key=plain_key
        )

    @strawberry.mutation(
        description="Delete an API key for good. You can't delete your own key. Admin only."
    )
    async def revoke_api_key(
        self,
        info: strawberry.Info[GraphQLContext, None],
        key_id: int
    ) -> bool:
        if not info.context.is_admin:
            raise Exception("Admin access required")

        if info.context.api_key.id == key_id:
            raise Exception("Cannot revoke your own API key")

        key = info.context.auth_db.exec(
            select(ApiKey).where(ApiKey.id == key_id)
        ).first()

        if not key:
            raise Exception(f"API key with ID {key_id} not found")

        revoked = await AuthService.revoke_api_key(key_id, info.context.auth_db)

        if revoked:
            logger.info(f"Admin '{info.context.api_key.name}' revoked API key '{key.name}' (ID: {key_id}) via GraphQL")

        return revoked


# Create the GraphQL schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[DBSessionCleanupExtension, LimitCapExtension],
    types=[
        # Auth types
        ApiKeyType, ApiUsageType, AuthStatsType, ApiKeyUsageStatsType, UserRoleType,
        # Discord types
        UserType, MessageActivityType, VoiceSessionType, ActivityLogType,
        PresenceStatusLogType, CustomStatusType, UserNameHistoryType,
        ChannelStatsType, ServerStatsType, UserStatsType,
        DailyStatsType, HourlyDistributionType, TopItemType, TopUserType,
        TopVoiceStateUserType, UniqueActivityType, VoiceConnectionType,
        # Enums
        ActivityTypeEnum, MessageTypeEnum, DiscordStatusEnum, VoiceStateTypeEnum
    ]
)

# Create the FastAPI GraphQL router
graphql_app = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
    graphql_ide="graphiql"
)
