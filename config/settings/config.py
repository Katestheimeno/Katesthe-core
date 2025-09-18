"""
Centralized configuration using pydantic-settings.
Path: config/settings/config.py

This module provides a centralized configuration structure using pydantic-settings
with separate settings classes for different concerns (database, email, etc.)
"""
import os
from pathlib import Path
from typing import List
from pydantic import Field, field_validator
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
    # Check DJANGO_ENV first
    django_env = os.getenv('DJANGO_ENV', '').lower()
    if django_env in ['local', 'prod', 'test', 'prof']:
        return str(BASE_DIR / f".env.{django_env}")
    
    # Check DJANGO_SETTINGS_MODULE
    settings_module = os.getenv('DJANGO_SETTINGS_MODULE', '')
    if 'local' in settings_module:
        return str(BASE_DIR / '.env.local')
    elif 'production' in settings_module:
        return str(BASE_DIR / '.env.prod')
    elif 'test' in settings_module:
        return str(BASE_DIR / '.env.test')
    elif 'profiling' in settings_module:
        return str(BASE_DIR / '.env.prof')
    
    # Default to local
    return str(BASE_DIR / '.env.local')


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    USER: str = Field(default="postgres", alias="POSTGRES_USER", description="PostgreSQL username")
    PASSWORD: str = Field(default="postgres", alias="POSTGRES_PASSWORD", description="PostgreSQL password")
    HOST: str = Field(default="db", alias="POSTGRES_HOST", description="PostgreSQL host")
    PORT: int = Field(default=5432, alias="POSTGRES_PORT", description="PostgreSQL port")
    DB: str = Field(default="drf_starter", alias="POSTGRES_DB", description="PostgreSQL database name")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct the full database URL."""
        return f"postgresql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"


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
        # If BROKER_URL is not set, use Redis URL
        if not self.BROKER_URL:
            redis_settings = RedisSettings()
            self.BROKER_URL = redis_settings.URL


class ProjectSettings(BaseSettings):
    """Project branding and configuration settings."""
    
    NAME: str = Field(default="Katesthe-core", description="Project name")
    DESCRIPTION: str = Field(
        default="A Django REST Framework starter project with ready-to-use authentication, custom user management, and modular app structure.",
        description="Project description"
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
        extra="ignore"
    )
    
    # Core Django settings
    DJANGO_DEBUG: bool = Field(default=True, alias="DEBUG", description="Django debug mode")
    SECRET_KEY: str = Field(description="Django secret key")
    JWT_SECRET_KEY: str = Field(description="JWT secret key")
    ALLOWED_HOSTS: str = Field(default="*", description="Allowed hosts (comma-separated)")
    
    # Web server settings
    WEB_PORT: int = Field(default=8000, description="Web server port")
    
    # Database settings (direct environment variables)
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="postgres", description="PostgreSQL password")
    POSTGRES_HOST: str = Field(default="db", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="drf_starter", description="PostgreSQL database name")
    
    # Redis settings (direct environment variables)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
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
        description="Project description"
    )
    PROJECT_VERSION: str = Field(default="1.0.0", description="Project version")
    
    # Contact settings (direct environment variables)
    CONTACT_NAME: str = Field(default="Katesthe-core Dev Team", description="Contact name")
    CONTACT_EMAIL: str = Field(default="support@katesthe-core.com", description="Contact email")
    CONTACT_URL: str = Field(default="https://github.com/katesthe-core", description="Contact URL")
    
    # Theme settings (direct environment variables)
    THEME_PRIMARY_COLOR: str = Field(default="#6a0dad", description="Primary theme color")
    THEME_ACCENT_COLOR: str = Field(default="#4b0082", description="Accent theme color")
    
    # Nested settings (for backward compatibility and computed properties)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    project: ProjectSettings = Field(default_factory=ProjectSettings)
    contact: ContactSettings = Field(default_factory=ContactSettings)
    theme: ThemeSettings = Field(default_factory=ThemeSettings)
    
    # Computed properties for backward compatibility
    @property
    def DEBUG(self) -> bool:
        return self.DJANGO_DEBUG
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct the full database URL."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL


# Create the global settings instance
settings = MainSettings()
