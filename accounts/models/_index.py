"""
This is the custom user model for the DRF starter
alongside its custom account manager.
"""

from django.apps import apps
from rest_framework.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import (
    AbstractBaseUser,   # Base class for custom user models without username/password defaults
    PermissionsMixin,   # Provides permission fields like is_superuser, groups, user_permissions
    BaseUserManager,    # Base class to create custom user manager
)


imports = []


class CustomAccountManager(BaseUserManager):
    """
    Custom manager for the User model.
    Handles user and superuser creation logic.
    """

    def create_user(self, email, username, password=None, **other_fields):
        """
        Creates and saves a regular user with the given email, username, and password.
        """
        if not email:
            raise ValueError(_("You must provide an email address"))
        if not username:
            raise ValueError(_("You must provide a username"))

        # Normalize the email (lowercase domain part)
        email = self.normalize_email(email)
        # Create a new user instance
        user = self.model(email=email, username=username, **other_fields)
        # Hash and set the password
        user.set_password(password)
        # Save the user into the DB using the defined database
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **other_fields):
        """
        Creates and saves a superuser (admin).
        Ensures proper flags are set.
        """
        # Default flags for a superuser
        other_fields.setdefault("is_staff", True)
        other_fields.setdefault("is_superuser", True)
        other_fields.setdefault("is_active", True)

        # Sanity checks
        if other_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must be assigned to is_staff=True."))
        if other_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must be assigned to is_superuser=True."))

        return self.create_user(email, username, password, **other_fields)


imports += ["User"]


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for authentication.
    Extends:
    - AbstractBaseUser: Provides password & authentication handling.
    - PermissionsMixin: Adds fields & methods for Django's permission system.
    """

    # === Core Identity Fields ===
    username = models.CharField(
        _("username"),
        unique=True,
        max_length=30,
        help_text=_("Required. 30 characters or fewer."),
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    email = models.EmailField(
        _("email address"),
        unique=True,
        error_messages={
            "unique": _("A user with that email already exists."),
        },
    )

    # === Status Flags ===
    is_active = models.BooleanField(_("active"), default=False)  # Can login?
    is_staff = models.BooleanField(_("staff status"), default=False)  # Access admin site?
    is_verified = models.BooleanField(_("email verified"), default=False)  # Email confirmation done?

    # === Tracking Fields ===
    date_joined = models.DateTimeField(_("date joined"), default=now)
    last_login = models.DateTimeField(_("last login"), blank=True, null=True)
    updated_at = models.DateTimeField(_("last updated"), auto_now=True)

    # === Manager ===
    objects = CustomAccountManager()

    # === Configuration ===
    USERNAME_FIELD = "email"       # Email is used for authentication instead of username
    REQUIRED_FIELDS = ["username"] # Required when creating a superuser via CLI

    class Meta:
        db_table = "users"  # Explicit table name
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        indexes = [
            models.Index(fields=["email"]),                # Speed up lookups by email
            models.Index(fields=["username"]),             # Speed up lookups by username
            models.Index(fields=["is_active", "is_verified"]), # For queries filtering active/verified users
        ]
        ordering = ["-date_joined"]  # Newest users first

    def __str__(self):
        """String representation (shown in admin, shell, etc.)"""
        return self.username


# Export only the User model when using `from module import *`
__all__ = imports

