"""
Reusable abstract model: adds name and description fields.
Path: utils/models/namedescription.py
"""

from django.db import models

imports = []

imports += ["NameDescriptionModel"]


class NameDescriptionModel(models.Model):
    """
    Abstract model that adds a standard `name` and `description` field.
    
    Fields:
        name (CharField):
            - Short human-readable identifier for the object.
            - Commonly used in categories, tags, labels, etc.
        
        description (TextField):
            - Longer optional text providing details about the object.
            - Useful for tooltips, documentation, or SEO content.
    """

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ["name"]  # Default alphabetical ordering for convenience

    def __str__(self):
        return self.name


__all__ = imports

