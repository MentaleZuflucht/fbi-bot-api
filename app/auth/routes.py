"""
Admin REST endpoints for API key management.

These endpoints allow admins to create, list, and manage API keys
via HTTP requests. All endpoints require admin authentication.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth.database import get_auth_db
from app.auth.dependencies import AdminUser
from app.auth.models import ApiKey
from app.auth.schemas import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreateResponse,
    UsageStatsResponse
)
from app.auth.services import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/api-keys", tags=["Admin"])


@router.post(
    "/",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="""
    Create a new API key for a user.

    **Important**: The API key will only be shown once in the response.
    Make sure to save it securely - it cannot be retrieved later!
    """
)
async def create_api_key(
    key_data: ApiKeyCreate,
    admin: ApiKey = Depends(AdminUser),
    db: Session = Depends(get_auth_db)
):
    """Create a new API key (admin only)."""
    try:
        api_key_obj, plain_key = await AuthService.create_api_key(
            name=key_data.name,
            role=key_data.role.value,
            db=db
        )

        logger.info(f"Admin {admin.name} created API key '{key_data.name}'")

        return ApiKeyCreateResponse(
            id=api_key_obj.id,
            name=api_key_obj.name,
            key_prefix=api_key_obj.key_prefix,
            role=api_key_obj.role,
            created_at=api_key_obj.created_at,
            last_used_at=api_key_obj.last_used_at,
            api_key=plain_key
        )
    except Exception as e:
        logger.error(f"Error creating API key: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.get(
    "/",
    response_model=List[ApiKeyResponse],
    summary="List all API keys",
    description="Get a list of all API keys (admin only)."
)
async def list_api_keys(
    admin: ApiKey = Depends(AdminUser),
    db: Session = Depends(get_auth_db)
):
    """List all API keys (admin only)."""
    try:
        keys = db.exec(
            select(ApiKey).order_by(ApiKey.created_at.desc())
        ).all()

        return [ApiKeyResponse(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            role=key.role,
            created_at=key.created_at,
            last_used_at=key.last_used_at
        ) for key in keys]
    except Exception as e:
        logger.error(f"Error listing API keys: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
    description="Permanently delete an API key (admin only)."
)
async def revoke_api_key(
    key_id: int,
    admin: ApiKey = Depends(AdminUser),
    db: Session = Depends(get_auth_db)
):
    """Revoke (delete) an API key (admin only)."""
    try:
        # Check if key exists
        key = db.exec(select(ApiKey).where(ApiKey.id == key_id)).first()
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key with ID {key_id} not found"
            )

        # Prevent admins from revoking their own key
        if key.id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revoke your own API key"
            )

        success = await AuthService.revoke_api_key(key_id, db)

        if success:
            logger.info(f"Admin {admin.name} revoked API key '{key.name}' (ID: {key_id})")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke API key"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}"
        )


@router.get(
    "/{key_id}/stats",
    response_model=UsageStatsResponse,
    summary="Get usage statistics for an API key",
    description="Get usage statistics for a specific API key (admin only)."
)
async def get_key_stats(
    key_id: int,
    days: int = 7,
    admin: ApiKey = Depends(AdminUser),
    db: Session = Depends(get_auth_db)
):
    """Get usage statistics for an API key (admin only)."""
    try:
        key = db.exec(select(ApiKey).where(ApiKey.id == key_id)).first()
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key with ID {key_id} not found"
            )

        stats = await AuthService.get_usage_stats(key, db, days=days)

        return UsageStatsResponse(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting key stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get key stats: {str(e)}"
        )
