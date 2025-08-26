from django.db import models
imports = []

imports += ["SoftDeleteModel"]


class SoftDeleteModel(models.Model):
    """
    Abstract model that adds a soft-delete mechanism.
    Instead of deleting objects from the database, it flags them as deleted.
    """

    is_deleted = models.BooleanField(default=False)

    def delete(self, using=None, keep_parents=False):
        """Override delete() to perform a soft delete"""
        self.is_deleted = True
        self.save()

    class Meta:
        abstract = True


__all__ = imports
