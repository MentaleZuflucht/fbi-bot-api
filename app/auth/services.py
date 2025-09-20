"""
Authentication business logic and services.

This module contains all the business logic for authentication,
API key management, rate limiting, and audit logging.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
import json

from app.auth.models import ApiKey, ApiUsage

# Get logger for this module
logger = logging.getLogger(__name__)


class AuthService:
    """Service class for authentication operations."""

    @staticmethod
    async def authenticate_api_key(api_key: str, db: Session) -> Optional[ApiKey]:
        """
        Authenticate an API key.

        Args:
            api_key: The API key to validate
            db: Database session

        Returns:
            ApiKey if valid, None otherwise
        """
        # Hash the provided key
        key_hash = ApiKey.hash_key(api_key)

        # Find the API key in database
        db_api_key = db.exec(
            select(ApiKey)
            .where(ApiKey.key_hash == key_hash)
        ).first()

        if not db_api_key:
            logger.warning(f"Invalid API key attempt: {api_key[:20]}...")
            return None

        # Update last used timestamp
        db_api_key.last_used_at = datetime.now(timezone.utc)
        db.add(db_api_key)
        db.commit()

        # Return the API key
        logger.debug(f"Successfully authenticated API key: {db_api_key.name}")
        return db_api_key

    @staticmethod
    async def create_api_key(
        name: str,
        role: str,
        allowed_ips: List[str],
        db: Session
    ) -> tuple[ApiKey, str]:
        """
        Create a new API key.

        Args:
            name: Human-readable name for the key
            role: Role for the key (admin/read)
            allowed_ips: List of allowed IP addresses/CIDR blocks/DNS names
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
            role=role,
            allowed_ips=json.dumps(allowed_ips)
        )

        db.add(db_api_key)
        db.commit()
        db.refresh(db_api_key)

        # Log the key creation
        logger.info(f"Created API key '{name}' with role '{role}'")

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

    @staticmethod
    async def get_usage_stats(api_key: ApiKey, db: Session, days: int = 7) -> Dict[str, Any]:
        """
        Get simple usage statistics for an API key.

        Args:
            api_key: The API key to get stats for
            db: Database session
            days: Number of days to look back

        Returns:
            dict: Usage statistics
        """
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Total requests in period
        total_requests = db.exec(
            select(ApiUsage)
            .where(ApiUsage.api_key_id == api_key.id)
            .where(ApiUsage.timestamp >= start_date)
        ).count()

        # Requests today
        requests_today = db.exec(
            select(ApiUsage)
            .where(ApiUsage.api_key_id == api_key.id)
            .where(ApiUsage.timestamp >= today_start)
        ).count()

        # Error count in period
        error_requests = db.exec(
            select(ApiUsage)
            .where(ApiUsage.api_key_id == api_key.id)
            .where(ApiUsage.timestamp >= start_date)
            .where(ApiUsage.response_status >= 400)
        ).count()

        return {
            "total_requests": total_requests,
            "requests_today": requests_today,
            "error_requests": error_requests,
            "success_rate": ((total_requests - error_requests) / total_requests * 100) if total_requests else 100.0,
            "period_days": days
        }
