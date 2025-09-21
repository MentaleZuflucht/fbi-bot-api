from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from sqlmodel import SQLModel, Field, Index, Relationship
from sqlalchemy import UniqueConstraint
import hashlib
import secrets


class UserRole(str, Enum):
    """
    - ADMIN: Full access including user management endpoints
    - READ: Read-only access to Discord bot data
    """
    ADMIN = "admin"
    READ = "read"


class ApiKey(SQLModel, table=True):
    """
    API keys for bearer token authentication.

    Everything you need in one simple table:
    - The token (hashed for security)
    - Role (admin/read permissions)
    - Name (so you know which friend this belongs to)
    - Basic tracking (created/last used)
    """
    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
        Index("ix_api_keys_key_hash", "key_hash"),
        Index("ix_api_keys_key_prefix", "key_prefix"),
        Index("ix_api_keys_role", "role"),
        Index("ix_api_keys_created_at", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    key_hash: str = Field(
        max_length=64,
        description="SHA-256 hash of the API key"
    )
    key_prefix: str = Field(
        max_length=20,
        description="Key prefix for identification (e.g., 'sk_live_abc12345')"
    )

    name: str = Field(
        max_length=100,
        description="Human-readable name (e.g., 'John's Key', 'Alice Discord Access')"
    )

    role: UserRole = Field(default=UserRole.READ, description="Access level (admin/read)")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Key generation timestamp"
    )
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="Last successful authentication"
    )

    usage_logs: List["ApiUsage"] = Relationship(
        back_populates="api_key",
        cascade_delete=True
    )

    @staticmethod
    def generate_key() -> tuple[str, str]:
        """
        Generate a new API key and its hash.

        Returns:
            tuple: (api_key, key_hash) where api_key is the plain text key
                   and key_hash is the SHA-256 hash for database storage
        """

        key_bytes = secrets.token_bytes(32)
        api_key = f"sk_live_{key_bytes.hex()}"

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        return api_key, key_hash

    @staticmethod
    def extract_key_prefix(api_key: str) -> str:
        """
        Extract the key prefix for database storage.

        The prefix is the first 20 characters of the API key, which includes
        the 'sk_live_' prefix and the first 12 characters of the hex token.
        This provides enough information for identification while fitting
        within the database field limit.

        Args:
            api_key: The full API key

        Returns:
            str: The key prefix (exactly 20 characters)

        Raises:
            ValueError: If the API key is too short to generate a valid prefix
        """
        if len(api_key) < 20:
            raise ValueError(f"API key too short: expected at least 20 characters, got {len(api_key)}")

        prefix = api_key[:20]

        if not prefix.startswith('sk_live_'):
            raise ValueError(f"Invalid API key format: expected to start with 'sk_live_', got '{prefix[:8]}'")

        return prefix

    @staticmethod
    def hash_key(api_key: str) -> str:
        """Hash an API key for database lookup."""
        return hashlib.sha256(api_key.encode()).hexdigest()


class ApiUsage(SQLModel, table=True):
    """
    Simple API usage tracking.

    Just the basics to see how much your API is being used:
    - When was the request made
    - Which endpoint was called
    - Which friend made the request
    """
    __tablename__ = "api_usage"
    __table_args__ = (
        Index("ix_api_usage_api_key_id", "api_key_id"),
        Index("ix_api_usage_timestamp", "timestamp"),
        Index("ix_api_usage_endpoint", "endpoint"),
        Index("ix_api_usage_key_time", "api_key_id", "timestamp"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    api_key_id: int = Field(foreign_key="api_keys.id", description="Which API key was used")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the request was made"
    )
    endpoint: str = Field(
        max_length=200,
        description="API endpoint that was called (e.g., '/api/discord/users')"
    )
    method: str = Field(
        max_length=10,
        description="HTTP method (GET, POST, etc.)"
    )

    response_status: Optional[int] = Field(
        default=None,
        description="HTTP response status (200, 404, etc.)"
    )

    api_key: ApiKey = Relationship(back_populates="usage_logs")


__all__ = [
    "UserRole",
    "ApiKey",
    "ApiUsage",
]
