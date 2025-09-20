"""
Pydantic schemas for auth-related API requests and responses.

These schemas define the shape of data for API endpoints,
separate from the database models to allow for different
representations (e.g., hiding sensitive fields).
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.auth.models import UserRole


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key."""
    name: str = Field(..., max_length=100, description="Human-readable name for the key")
    role: UserRole = Field(default=UserRole.READ, description="Role for the key (admin/read)")
    allowed_ips: List[str] = Field(..., description="List of allowed IP addresses/CIDR blocks/DNS names")


class ApiKeyResponse(BaseModel):
    """Schema for API key responses (without sensitive data)."""
    id: int
    name: str
    key_prefix: str
    role: UserRole
    created_at: datetime
    last_used_at: Optional[datetime]
    allowed_ips: List[str]  # Will be parsed from JSON

    class Config:
        from_attributes = True


class ApiKeyCreateResponse(ApiKeyResponse):
    """Schema for API key creation response (includes the actual key)."""
    api_key: str


class ApiUsageResponse(BaseModel):
    """Schema for API usage log entries."""
    id: int
    timestamp: datetime
    endpoint: str
    method: str
    response_status: Optional[int]
    api_key_name: str

    class Config:
        from_attributes = True


class UsageStatsResponse(BaseModel):
    """Schema for API usage statistics."""
    total_requests: int
    requests_today: int
    error_requests: int
    success_rate: float
    period_days: int


class AuthStatsResponse(BaseModel):
    """Schema for overall authentication statistics."""
    total_api_keys: int
    admin_keys: int
    read_keys: int
    total_requests_today: int
