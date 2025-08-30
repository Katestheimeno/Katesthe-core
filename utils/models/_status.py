"""
Reusable abstract model: dynamic status field.
Path: utils/models/status.py
"""

from django.db import models

imports = []

imports += ["StatusModel"]


class StatusModel(models.Model):
    """
    Abstract model that adds a `status` field.
    
    The choices for the status field are not hardcoded here.
    Instead, each subclass should define its own STATUS_CHOICES class attribute.
    
    Example:
        class Post(StatusModel):
            STATUS_CHOICES = [
                ("draft", "Draft"),
                ("published", "Published"),
                ("archived", "Archived"),
            ]
            title = models.CharField(max_length=255)
    """

    status = models.CharField(
        max_length=50,
        choices=[],  # Will be overridden dynamically
        default=None,
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # If subclass defines STATUS_CHOICES, inject them into field dynamically
        if hasattr(self, "STATUS_CHOICES") and self.STATUS_CHOICES:
            self._meta.get_field("status").choices = self.STATUS_CHOICES
            if self.status is None:
                self.status = self.STATUS_CHOICES[0][0]  # default to first choice
        super().save(*args, **kwargs)


__all__ = imports

