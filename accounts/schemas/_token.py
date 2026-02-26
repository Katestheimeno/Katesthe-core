"""
Pydantic schemas for JWT and activation (auth/token domain).
Path: accounts/schemas/_token.py
"""

from typing import Optional

from pydantic import BaseModel, Field


class JWTTokenCreateRequest(BaseModel):
    """Request schema for JWT token creation (login)."""

    username: str = Field(
        ...,
        description="Username or email address for login.",
    )
    password: str = Field(..., min_length=1, description="User password.")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "password": "securepassword123",
            }
        }


class JWTTokenUserResponse(BaseModel):
    """Nested user object in JWT token response."""

    id: int
    username: str
    email: str
    is_verified: bool

    class Config:
        from_attributes = True


class JWTTokenCreateResponse(BaseModel):
    """Response schema for JWT token creation (login)."""

    refresh: str = Field(..., description="Refresh token.")
    access: str = Field(..., description="Access token.")
    user: JWTTokenUserResponse = Field(..., description="Authenticated user summary.")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "user": {
                    "id": 1,
                    "username": "johndoe",
                    "email": "john@example.com",
                    "is_verified": True,
                },
            }
        }


class JWTLogoutRequest(BaseModel):
    """Request schema for JWT logout (token blacklist)."""

    refresh: Optional[str] = Field(
        None,
        description="Refresh token to blacklist. Optional; if omitted, access token expires naturally.",
    )

    class Config:
        json_schema_extra = {
            "example": {"refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."}
        }


class ActivationResponse(BaseModel):
    """Response schema for user activation endpoint."""

    success: bool = Field(..., description="Whether activation succeeded.")
    message: str = Field(..., description="Human-readable message.")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Account activated successfully! You can now log in.",
            }
        }


class JWTRefreshRequest(BaseModel):
    """Request schema for JWT token refresh."""

    refresh: str = Field(..., description="Refresh token.")

    class Config:
        json_schema_extra = {"example": {"refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."}}


class JWTRefreshResponse(BaseModel):
    """Response schema for JWT token refresh."""

    access: str = Field(..., description="New access token.")

    class Config:
        json_schema_extra = {"example": {"access": "eyJ0eXAiOiJKV1QiLCJhbGc..."}}


class JWTVerifyRequest(BaseModel):
    """Request schema for JWT token verification."""

    token: str = Field(..., description="Access or refresh token to verify.")

    class Config:
        json_schema_extra = {"example": {"token": "eyJ0eXAiOiJKV1QiLCJhbGc..."}}
