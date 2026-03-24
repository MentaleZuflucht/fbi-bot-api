"""
Authentication routes for frontend access.

Simple password-based authentication that issues JWT tokens for the frontend.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from sqlmodel import Session

from app.auth.database import get_auth_db
from app.auth.services import AuthService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# Configuration from settings


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create a JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_frontend_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """Verify JWT token from frontend."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        token_type: str = payload.get("type")

        if token_type != "frontend":
            raise credentials_exception

        return payload
    except JWTError:
        raise credentials_exception


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Frontend login endpoint.

    Validates password and returns a JWT token for accessing the GraphQL API.
    """
    if request.password != settings.frontend_password:
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


@router.get("/verify")
async def verify_token(payload: Annotated[dict, Depends(verify_frontend_token)]):
    """
    Verify if a token is valid.

    Useful for checking authentication status.
    """
    return {"valid": True, "type": payload.get("type")}
