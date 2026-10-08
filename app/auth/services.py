"""
API key management and usage logging.
"""
import logging
from typing import Optional
from sqlmodel import Session, select

from app.auth.models import ApiKey, ApiUsage

# Get logger for this module
logger = logging.getLogger(__name__)


class AuthService:
    """Service class for API key operations."""

    @staticmethod
    async def create_api_key(
        name: str,
        role: str,
        db: Session
    ) -> tuple[ApiKey, str]:
        """
        Create a new API key.

        Args:
            name: Human-readable name for the key
            role: Role for the key (admin/read)
            db: Database session

        Returns:
            tuple: (ApiKey object, plain text API key)
        """
        # Generate new API key
        api_key_plain, key_hash = ApiKey.generate_key()
        key_prefix = ApiKey.extract_key_prefix(api_key_plain)

        # Create database record
        db_api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            role=role
        )

        db.add(db_api_key)
        db.commit()
        db.refresh(db_api_key)

        # Log the key creation
        logger.info(f"Created API key '{name}' with role '{role}' (ID: {db_api_key.id})")

        return db_api_key, api_key_plain

    @staticmethod
    async def revoke_api_key(key_id: int, db: Session) -> bool:
        """
        Revoke (delete) an API key.

        Args:
            key_id: ID of the key to revoke
            db: Database session

        Returns:
            bool: True if revoked successfully
        """
        api_key = db.exec(select(ApiKey).where(ApiKey.id == key_id)).first()
        if not api_key:
            return False

        # Log the revocation
        logger.info(f"Revoked API key '{api_key.name}' (ID: {key_id})")

        # Delete the key (this will cascade delete usage logs)
        db.delete(api_key)
        db.commit()

        return True

    @staticmethod
    async def record_api_usage(
        api_key: ApiKey,
        endpoint: str,
        method: str,
        response_status: Optional[int] = None,
        db: Session = None
    ):
        """
        Record API usage for simple tracking.

        Args:
            api_key: The API key used
            endpoint: API endpoint called
            method: HTTP method
            response_status: HTTP response status
            db: Database session
        """
        if db is None:
            return  # Skip if no DB session provided

        # Record simple usage
        usage = ApiUsage(
            api_key_id=api_key.id,
            endpoint=endpoint,
            method=method,
            response_status=response_status
        )
        db.add(usage)
        db.commit()
