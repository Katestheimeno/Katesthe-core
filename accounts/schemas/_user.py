"""
Pydantic schemas for user domain.
Path: accounts/schemas/_user.py

Request/response contracts for user create, update, detail, list, and delete.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class UserCreateRequest(BaseModel):
    """Request schema for user registration."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Username. 30 characters or fewer.",
    )
    email: str = Field(..., description="User email address.")
    password: str = Field(..., min_length=1, write_only=True, description="User password.")

    @field_validator("username")
    @classmethod
    def validate_username_lower(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Username cannot be empty or whitespace only.")
        return v.strip().lower()

    @field_validator("email", mode="before")
    @classmethod
    def validate_email_lower(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip().lower()
        if not v or "@" not in v:
            raise ValueError("Invalid email format.")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "securepassword123",
            }
        }


class UserUpdateRequest(BaseModel):
    """Request schema for updating current user (/me) or user detail."""

    username: Optional[str] = Field(None, min_length=1, max_length=30)
    email: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username_lower(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Username cannot be empty or whitespace only.")
        return v.strip().lower()

    @field_validator("email", mode="before")
    @classmethod
    def validate_email_lower(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if isinstance(v, str):
            v = v.strip().lower()
        if v and "@" not in v:
            raise ValueError("Invalid email format.")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe_updated",
                "email": "john.new@example.com",
            }
        }


class UserDeleteRequest(BaseModel):
    """Request schema for user account deletion."""

    current_password: str = Field(
        ...,
        min_length=1,
        description="Current password required to confirm account deletion.",
    )

    class Config:
        json_schema_extra = {
            "example": {"current_password": "currentpassword123"}
        }


class UserBaseResponse(BaseModel):
    """Base user response schema."""

    id: int
    username: str
    email: str
    is_active: bool
    is_verified: bool
    date_joined: datetime
    last_login: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(UserBaseResponse):
    """User detail response (admin/general use, includes is_staff)."""

    is_staff: bool = False

    class Config:
        from_attributes = True


class CurrentUserResponse(UserBaseResponse):
    """Current user response for /me endpoint."""

    class Config:
        from_attributes = True


class UserListResponse(UserBaseResponse):
    """User list item response."""

    is_staff: bool = False

    class Config:
        from_attributes = True


class UserListPaginatedResponse(BaseModel):
    """Paginated or plain list of users (for list endpoint)."""

    results: List[UserListResponse] = Field(
        default_factory=list,
        description="List of users.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "id": 1,
                        "username": "johndoe",
                        "email": "john@example.com",
                        "is_active": True,
                        "is_verified": True,
                        "date_joined": "2024-01-01T00:00:00Z",
                        "last_login": None,
                        "updated_at": "2024-01-01T00:00:00Z",
                        "is_staff": False,
                    }
                ]
            }
        }
