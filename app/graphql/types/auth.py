"""
GraphQL types for authentication and API key management.

These types expose the auth database for admin operations like
API key administration and usage tracking.
"""

from typing import Annotated, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum
import strawberry
from sqlmodel import select, func
from app.graphql.context import GraphQLContext
from app.graphql.permissions import IsAdmin
from app.auth.models import ApiKey, ApiUsage


@strawberry.enum(name="ApiKeyRole", description="What an API key may do.")
class UserRoleType(Enum):
    ADMIN = strawberry.enum_value("admin", description="Query data and manage API keys")
    READ = strawberry.enum_value("read", description="Query data")


@strawberry.type(
    name="ApiKey",
    description="An API key. The full key is never shown again after creating it.",
)
class ApiKeyType:
    id: int
    name: str = strawberry.field(description="Who the key is for.")
    key_prefix: str = strawberry.field(description="Start of the key, to recognize it.")
    role: UserRoleType
    created_at: datetime
    last_used_at: Optional[datetime]

    @strawberry.field(
        description="Request statistics of this key. Admin only.",
        permission_classes=[IsAdmin],
    )
    def usage_stats(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Annotated[int, strawberry.argument(description="Look back this many days.")] = 7
    ) -> "ApiKeyUsageStatsType":
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        usage_data = info.context.auth_db.exec(
            select(
                func.count(ApiUsage.id).label('total_requests'),
                func.count().filter(ApiUsage.response_status >= 400).label('error_count')
            )
            .where(ApiUsage.api_key_id == self.id)
            .where(ApiUsage.timestamp >= start_date)
        ).first()

        total_requests = usage_data.total_requests or 0
        error_count = usage_data.error_count or 0

        return ApiKeyUsageStatsType(
            total_requests=total_requests,
            error_count=error_count,
            success_rate=(
                ((total_requests - error_count) / total_requests * 100)
                if total_requests else 100.0
            )
        )

    @classmethod
    def from_model(cls, key: ApiKey) -> "ApiKeyType":
        """Create GraphQL type from database model."""
        return cls(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            role=UserRoleType(key.role.value),
            created_at=key.created_at,
            last_used_at=key.last_used_at
        )


@strawberry.type(name="ApiKeyUsageStats", description="Request statistics of one API key.")
class ApiKeyUsageStatsType:
    total_requests: int
    error_count: int = strawberry.field(description="Requests that returned errors.")
    success_rate: float = strawberry.field(description="Percentage of successful requests, 0-100.")


@strawberry.type(name="ApiUsage", description=(
    "One logged API request. Only requests made with an API key are logged, "
    "not the website's."
))
class ApiUsageType:
    id: int
    timestamp: datetime
    endpoint: str = strawberry.field(
        description='What was queried, e.g. "/graphql: users, topUsers".'
    )
    method: str = strawberry.field(description="HTTP method, e.g. POST.")
    response_status: Optional[int] = strawberry.field(
        description="200 if the request worked, 400 if it returned errors."
    )
    api_key_name: str = strawberry.field(description="Name of the API key that made the request.")

    @classmethod
    def from_model(cls, usage: ApiUsage, api_key_name: str) -> "ApiUsageType":
        """Create GraphQL type from database model."""
        return cls(
            id=usage.id,
            timestamp=usage.timestamp,
            endpoint=usage.endpoint,
            method=usage.method,
            response_status=usage.response_status,
            api_key_name=api_key_name
        )


@strawberry.type(name="AuthStats", description="Overview of API keys and requests.")
class AuthStatsType:
    total_api_keys: int
    admin_keys: int
    read_keys: int
    total_requests_today: int = strawberry.field(description="Requests since midnight UTC.")


@strawberry.type(description="A newly created API key.")
class CreateApiKeyResult:
    id: int
    name: str
    key_prefix: str
    role: UserRoleType
    created_at: datetime
    api_key: str = strawberry.field(
        description="The full key. It is only shown this once, so save it now."
    )
