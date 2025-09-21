"""
GraphQL types for authentication and API key management.

These types expose the auth database for admin operations like
API key administration and usage tracking.
"""

from typing import Optional
from datetime import datetime
from enum import Enum
import strawberry
from sqlmodel import select, func
from app.graphql.context import GraphQLContext
from app.auth.models import ApiKey, ApiUsage


@strawberry.enum
class UserRoleType(Enum):
    """GraphQL enum for API key roles."""
    ADMIN = "admin"
    READ = "read"


@strawberry.type
class ApiKeyType:
    """GraphQL type for API keys."""
    id: int
    name: str
    key_prefix: str  # Only show prefix, never full key
    role: UserRoleType
    created_at: datetime
    last_used_at: Optional[datetime]

    @strawberry.field
    def usage_stats(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: int = 7
    ) -> "ApiKeyUsageStatsType":
        """Get usage statistics for this API key."""
        if not info.context.is_admin:
            raise Exception("Admin access required")

        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)

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


@strawberry.type
class ApiKeyUsageStatsType:
    """Statistics for API key usage."""
    total_requests: int
    error_count: int
    success_rate: float


@strawberry.type
class ApiUsageType:
    """GraphQL type for API usage logs."""
    id: int
    timestamp: datetime
    endpoint: str
    method: str
    response_status: Optional[int]
    api_key_name: str  # From the related API key

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


@strawberry.type
class AuthStatsType:
    """Overall authentication statistics."""
    total_api_keys: int
    admin_keys: int
    read_keys: int
    total_requests_today: int
