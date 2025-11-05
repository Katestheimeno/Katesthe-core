"""
Reusable abstract model: auto-generate slug dynamically from a best-matching field.
Path: utils/models/slugger.py
"""

from django.utils.text import slugify
from django.db import models


class SluggedModel(models.Model):
    """
    Abstract model that provides a `slug` field.

    Automatically generates a slug from the first available field in
    `slug_source_fields` (defaults to ['name', 'title', 'label']).

    You can override `slug_source_fields` in subclasses if needed.

    Example:
        class Category(SluggedModel):
            name = models.CharField(max_length=100)

        class Article(SluggedModel):
            title = models.CharField(max_length=200)
    """

    slug = models.SlugField(max_length=255, unique=True, blank=True)
    slug_source_fields = ["name", "title", "label"]

    def get_slug_source(self):
        """
        Determines which field to use for generating the slug.
        Override this method if you want custom logic.
        """
        for field in getattr(self, "slug_source_fields", []):
            value = getattr(self, field, None)
            if value:
                return value
        return None

    def save(self, *args, **kwargs):
        if not self.slug:
            source = self.get_slug_source()
            if source:
                self.slug = slugify(source)
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


__all__ = ["SluggedModel"]
