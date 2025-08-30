"""
Reusable abstract model: dynamic enum fields.
Path: utils/models/enum.py
"""

from django.db import models

imports = []

imports += ["DynamicEnumModel"]


class DynamicEnumModel(models.Model):
    """
    Abstract model that allows child models to define
    multiple dynamic choice fields by convention.

    Usage:
        class Task(DynamicEnumModel):
            STATUS_CHOICES = [
                ("todo", "To Do"),
                ("in_progress", "In Progress"),
                ("done", "Done"),
            ]
            PRIORITY_CHOICES = [
                ("low", "Low"),
                ("medium", "Medium"),
                ("high", "High"),
            ]

            status = models.CharField(max_length=20)
            priority = models.CharField(max_length=20)
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        On save, assign dynamic choices to all enum-like fields.
        Convention: a field `foo` will look for `FOO_CHOICES` on the class.
        """
        for field in self._meta.fields:
            if isinstance(field, models.CharField):
                choice_attr = f"{field.name.upper()}_CHOICES"
                if hasattr(self, choice_attr):
                    field.choices = getattr(self, choice_attr)

                    # Set default if empty
                    if not getattr(self, field.name):
                        setattr(self, field.name, field.choices[0][0])

        super().save(*args, **kwargs)

