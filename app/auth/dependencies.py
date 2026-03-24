"""
Authentication dependencies for FastAPI.

Provides dependency injection for authentication, authorization,
and rate limiting across both REST and GraphQL endpoints.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select
import jwt

from app.auth.database import get_auth_db
from app.auth.models import ApiKey
from app.config import settings

# Get logger for this module
logger = logging.getLogger(__name__)


async def get_current_api_key(
    request: Request,
    auth_db: Session = Depends(get_auth_db)
) -> ApiKey:
    """
    Extract and validate API key or JWT token from request headers.

    Supports both:
    - API key authentication (for external/API access)
    - JWT token authentication (for frontend)

    Args:
        request: FastAPI request object
        auth_db: Auth database session

    Returns:
        ApiKey: Authenticated API key (or virtual key for JWT auth)

    Raises:
        HTTPException: If authentication fails
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use 'Bearer <token>'"
        )

    token = auth_header[len("Bearer "):].strip()

    # Try JWT token first (for frontend)
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") == "frontend":
            logger.debug("Frontend JWT authentication successful")
            # Create a virtual API key object for frontend access
            virtual_key = ApiKey(
                id=0,
                key_hash="frontend_jwt",
                key_prefix="frontend",
                name="Frontend User",
                role="read",
                created_at=datetime.now(timezone.utc)
            )
            return virtual_key
    except jwt.InvalidTokenError:
        pass

    # Try API key authentication
    key_hash = ApiKey.hash_key(token)
    api_key = auth_db.exec(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    ).first()

    if not api_key:
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(f"Authentication failed from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Update last used time
    api_key.last_used_at = datetime.now(timezone.utc)
    auth_db.add(api_key)
    auth_db.commit()

    return api_key


async def get_current_user(
    current_api_key: ApiKey = Depends(get_current_api_key)
) -> ApiKey:
    """
    Get current authenticated API key (alias for compatibility).

    Args:
        current_api_key: API key from get_current_api_key

    Returns:
        ApiKey: The authenticated API key
    """
    return current_api_key


async def get_admin_user(
    current_api_key: ApiKey = Depends(get_current_api_key)
) -> ApiKey:
    """
    Ensure the current API key has admin privileges.

    Args:
        current_api_key: Authenticated API key

    Returns:
        ApiKey: Admin API key

    Raises:
        HTTPException: If API key doesn't have admin role
    """
    if current_api_key.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_api_key


# Type aliases for easier imports
CurrentUser = Annotated[ApiKey, Depends(get_current_user)]
AdminUser = Annotated[ApiKey, Depends(get_admin_user)]
