"""
Reusable abstract model: created_at/updated_at timestamps.
Path: utils/models/timestamp.py
"""

from django.db import models

# Track what should be exposed when using: `from module import *`
imports = []
imports += ["TimeStampedModel"]


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides automatic tracking of
    creation and update timestamps.

    Fields:
        created_at (DateTimeField):
            - Automatically set to the current datetime when the object is first created.
            - Useful for knowing when a record was initially added.

        updated_at (DateTimeField):
            - Automatically updated to the current datetime every time the object is saved.
            - Helps track modifications and last change time.

    Usage:
        Inherit this class in any model where you want to automatically
        track creation and modification times.

    Example:
        class Post(TimeStampedModel):
            title = models.CharField(max_length=200)
            body = models.TextField()
    """

    created_at = models.DateTimeField(
        auto_now_add=True)  # Set only once on creation
    updated_at = models.DateTimeField(
        auto_now=True)      # Updated every save()

    class Meta:
        abstract = True  # Prevents Django from creating a separate DB table
        # Makes this class reusable across models


# Control what is exported with *
__all__ = imports
