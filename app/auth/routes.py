"""
Authentication routes for frontend access.

Simple password-based authentication that issues JWT tokens for the frontend.
"""
import logging
import secrets
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import jwt

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Failed logins are counted across all clients, since behind Cloudflare and the proxy
# the real client IP is unknown (and IP headers could be spoofed). During an attack
# this also blocks real users for up to a minute; logged-in users are not affected.
MAX_FAILED_LOGINS_PER_MINUTE = 10
_failed_logins: deque[float] = deque()


def _too_many_failed_logins() -> bool:
    cutoff = time.monotonic() - 60
    while _failed_logins and _failed_logins[0] < cutoff:
        _failed_logins.popleft()
    return len(_failed_logins) >= MAX_FAILED_LOGINS_PER_MINUTE


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Create a JWT token."""
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Frontend login endpoint.

    Validates password and returns a JWT token for accessing the GraphQL API.
    """
    if _too_many_failed_logins():
        logger.warning("Login blocked, too many failed attempts")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts, try again in a minute"
        )

    if not secrets.compare_digest(request.password.encode(), settings.frontend_password.encode()):
        _failed_logins.append(time.monotonic())
        logger.warning("Failed login attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )

    access_token = create_access_token(
        data={"type": "frontend", "sub": "frontend_user"},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes)
    )

    logger.info("Frontend login successful")

    return LoginResponse(access_token=access_token)
