from django.db import models
from django.conf import settings as cfg
imports = []

imports += ["TrackableModel"]


class TrackableModel(models.Model):
    """
    Abstract model that tracks the user who created and last updated the object.
    """

    created_by = models.ForeignKey(
        cfg.AUTH_USER_MODEL,
        related_name="%(class)s_created",
        null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    updated_by = models.ForeignKey(
        cfg.AUTH_USER_MODEL,
        related_name="%(class)s_updated",
        null=True, blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True


__all__ = imports
