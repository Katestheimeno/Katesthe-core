import uuid
from django.db import models

imports = []

imports += ["UUIDModel"]


class UUIDModel(models.Model):
    """
    Abstract model that replaces the default integer `id`
    with a UUID primary key for better scalability and security.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


__all__ = imports
