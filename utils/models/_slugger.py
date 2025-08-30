"""
Reusable abstract model: auto-generate slug from `name` if present.
Path: utils/models/slugger.py
"""

from django.utils.text import slugify
from django.db import models

imports = []

imports += ["SluggedModel"]



class SluggedModel(models.Model):
    """
    Abstract model that provides a slug field
    auto-generated from a 'name' or 'title'.
    """

    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug and hasattr(self, "name"):
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


__all__ = imports
