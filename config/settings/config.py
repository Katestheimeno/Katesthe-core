"""
Centralized configuration using pydantic-settings.
Path: config/settings/config.py

This module provides a centralized configuration structure using pydantic-settings
with separate settings classes for different concerns (database, email, etc.)
"""
import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Define the base directory of the project (2 levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def get_env_file_path() -> str:
    """
    Determine which environment file to use based on Django settings.

    Priority:
    1. DJANGO_ENV environment variable
    2. DJANGO_SETTINGS_MODULE environment variable
    3. Default to 'local'
    """
    django_env = os.getenv("DJANGO_ENV", "").lower()
    if django_env in ["local", "prod", "test"]:
        return str(BASE_DIR / f".env.{django_env}")

    settings_module = os.getenv("DJANGO_SETTINGS_MODULE", "")
    if "local" in settings_module:
        return str(BASE_DIR / ".env.local")
    if "production" in settings_module:
        return str(BASE_DIR / ".env.prod")
    if "test" in settings_module:
        return str(BASE_DIR / ".env.test")

    return str(BASE_DIR / ".env.local")


class EmailSettings(BaseSettings):
    """Email configuration settings."""

    HOST: str = Field(default="localhost", description="SMTP host")
    PORT: int = Field(default=1025, description="SMTP port")
    USE_TLS: bool = Field(default=False, description="Use TLS for SMTP")
    HOST_USER: str = Field(default="", description="SMTP username")
    HOST_PASSWORD: str = Field(default="", description="SMTP password")
    FRONTEND_DOMAIN: str = Field(default="", description="Frontend domain for email links")


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")


class CelerySettings(BaseSettings):
    """Celery configuration settings."""

    BROKER_URL: str = Field(default="", description="Celery broker URL")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.BROKER_URL:
            redis_settings = RedisSettings()
            self.BROKER_URL = redis_settings.URL


class ProjectSettings(BaseSettings):
    """Project branding and configuration settings."""

    NAME: str = Field(default="Katesthe-core", description="Project name")
    DESCRIPTION: str = Field(
        default="A Django REST Framework starter project with ready-to-use authentication, custom user management, and modular app structure.",
        description="Project description",
    )
    VERSION: str = Field(default="1.0.0", description="Project version")


class ContactSettings(BaseSettings):
    """Contact information settings."""

    NAME: str = Field(default="Katesthe-core Dev Team", description="Contact name")
    EMAIL: str = Field(default="support@katesthe-core.com", description="Contact email")
    URL: str = Field(default="https://github.com/katesthe-core", description="Contact URL")


class ThemeSettings(BaseSettings):
    """Theme color settings."""

    PRIMARY_COLOR: str = Field(default="#6a0dad", description="Primary theme color")
    ACCENT_COLOR: str = Field(default="#4b0082", description="Accent theme color")


class MainSettings(BaseSettings):
    """Main application settings that aggregates all other settings."""

    model_config = SettingsConfigDict(
        env_file=get_env_file_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Django settings
    DJANGO_DEBUG: bool = Field(default=True, alias="DEBUG", description="Django debug mode")
    SECRET_KEY: str = Field(description="Django secret key")
    JWT_SECRET_KEY: str = Field(description="JWT secret key")
    ALLOWED_HOSTS: str = Field(default="*", description="Allowed hosts (comma-separated)")

    # Web server settings
    WEB_PORT: int = Field(default=8000, description="Web server port")

    # Database (explicit primary; no DATABASE_URL for Django)
    USE_SQLITE: bool = Field(
        default=False,
        description="Force SQLite when True (overrides Postgres when both set).",
    )
    DB_PRIMARY_HOST: str = Field(default="", description="Postgres primary host; empty uses SQLite file")
    DB_PRIMARY_PORT: int = Field(default=5432, description="Postgres primary port")
    DB_PRIMARY_NAME: str = Field(default="drf_starter", description="Postgres database name")
    DB_PRIMARY_USER: str = Field(default="postgres", description="Postgres user")
    DB_PRIMARY_PASSWORD: str = Field(default="postgres", description="Postgres password")

    DB_REPLICA_HOSTS: str = Field(
        default="",
        description="Comma-separated replica hostnames (optional)",
    )
    DB_REPLICA_PORT: Optional[int] = Field(
        default=None,
        description="Replica port; defaults to DB_PRIMARY_PORT when unset",
    )
    DB_REPLICA_USER: str = Field(
        default="",
        description="Replica user; empty means same as primary",
    )
    DB_REPLICA_PASSWORD: str = Field(
        default="",
        description="Replica password; empty means same as primary",
    )
    DB_REPLICA_NAME: str = Field(
        default="",
        description="Replica database name; empty means same as primary",
    )
    DB_ROUTING_ENABLED: bool = Field(
        default=True,
        description="Use PrimaryReplicaRouter; reads go to healthy replicas when DB_REPLICA_HOSTS is set, else primary only",
    )

    # Redis settings (direct environment variables)
    REDIS_URL: str = Field(default="redis://redis:6379/0", description="Redis connection URL")

    # Sentry / error monitoring
    SENTRY_DSN: str = Field(default="", description="Sentry DSN; empty disables Sentry")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1, description="Sentry traces sample rate")

    # Debug payload middleware
    REQUEST_RESPONSE_DEBUG: bool = Field(default=False, description="Log request/response bodies (dev only)")

    # Email settings (direct environment variables)
    EMAIL_HOST: str = Field(default="localhost", description="SMTP host")
    EMAIL_PORT: int = Field(default=1025, description="SMTP port")
    EMAIL_USE_TLS: bool = Field(default=False, description="Use TLS for SMTP")
    EMAIL_HOST_USER: str = Field(default="", description="SMTP username")
    EMAIL_HOST_PASSWORD: str = Field(default="", description="SMTP password")
    EMAIL_FRONTEND_DOMAIN: str = Field(default="", description="Frontend domain for email links")

    # Project settings (direct environment variables)
    PROJECT_NAME: str = Field(default="Katesthe-core", description="Project name")
    PROJECT_DESCRIPTION: str = Field(
        default="A Django REST Framework starter project with ready-to-use authentication, custom user management, and modular app structure.",
        description="Project description",
    )
    PROJECT_VERSION: str = Field(default="1.0.0", description="Project version")

    # Contact settings (direct environment variables)
    CONTACT_NAME: str = Field(default="Katesthe-core Dev Team", description="Contact name")
    CONTACT_EMAIL: str = Field(default="support@katesthe-core.com", description="Contact email")
    CONTACT_URL: str = Field(default="https://github.com/katesthe-core", description="Contact URL")

    # Theme settings (direct environment variables)
    THEME_PRIMARY_COLOR: str = Field(default="#6a0dad", description="Primary theme color")
    THEME_ACCENT_COLOR: str = Field(default="#4b0082", description="Accent theme color")

    # JWT RS256
    JWT_RSA_PRIVATE_KEY: str = Field(default="", description="Base64-encoded PEM of the RSA private key for JWT RS256 signing")
    JWT_RSA_PREVIOUS_PUBLIC_KEY: str = Field(default="", description="Base64-encoded PEM of the previous public key (JWKS rotation window)")
    JWT_ISSUER: Optional[str] = Field(default=None, description="JWT iss claim")
    JWT_AUDIENCE: Optional[str] = Field(default=None, description="JWT aud claim")
    # Auth cookies
    AUTH_COOKIE_DOMAIN: str = Field(default="", description="Domain for auth cookies")
    AUTH_COOKIE_REFRESH_PATH: str = Field(default="/api/v1/auth/jwt/", description="Path scope for the refresh-token cookie")
    AUTH_COOKIE_SECURE: Optional[bool] = Field(default=None, description="Secure flag for auth cookies (None = auto from DEBUG)")
    AUTH_COOKIE_SAMESITE: Literal["Lax", "Strict", "None"] = Field(default="Lax", description="SameSite attribute for auth cookies")
    # Throttle toggle
    THROTTLE_ENABLED: bool = Field(default=True, description="Global toggle for all throttle classes. Set False for load testing.")

    # Nested settings
    email: EmailSettings = Field(default_factory=EmailSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    project: ProjectSettings = Field(default_factory=ProjectSettings)
    contact: ContactSettings = Field(default_factory=ContactSettings)
    theme: ThemeSettings = Field(default_factory=ThemeSettings)

    @property
    def DEBUG(self) -> bool:
        return self.DJANGO_DEBUG

    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL

    @model_validator(mode="after")
    def _validate_cookie_samesite(self) -> "MainSettings":
        """SameSite=None without the Secure attribute is rejected by browsers — fail fast."""
        if self.AUTH_COOKIE_SAMESITE == "None":
            effective_secure = (
                self.AUTH_COOKIE_SECURE
                if self.AUTH_COOKIE_SECURE is not None
                else not self.DJANGO_DEBUG
            )
            if not effective_secure:
                raise ValueError(
                    "AUTH_COOKIE_SAMESITE='None' requires secure cookies. "
                    "Set AUTH_COOKIE_SECURE=true (and serve over HTTPS) or use "
                    "SameSite 'Lax'/'Strict'."
                )
        return self


# Create the global settings instance
settings = MainSettings()
