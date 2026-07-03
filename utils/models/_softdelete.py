"""
Reusable abstract model: soft-delete via is_deleted flag.
Path: utils/models/_softdelete.py
"""

from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that filters out soft-deleted rows."""

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)

    def delete(self):
        """Soft-delete all rows in this queryset."""
        count = self.update(is_deleted=True)
        return (count, {self.model._meta.label: count})

    def hard_delete(self):
        """Permanently delete all rows — bypasses soft-delete."""
        return super().delete()


class SoftDeleteManager(models.Manager):
    """Manager that exposes only non-deleted rows.

    Provided as an *additional* manager (``alive_objects``).
    The default manager (``objects``) is intentionally left unfiltered
    so that admin, migrations, and existing code are not broken by an
    implicit queryset filter.
    """

    use_in_migrations = False

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """
    Abstract model that adds a soft-delete mechanism.
    Instead of deleting objects from the database, it flags them as deleted.

    Managers:
        objects        -- default, returns ALL rows (including soft-deleted).
        alive_objects  -- returns only rows where is_deleted=False.
    """

    is_deleted = models.BooleanField(default=False)

    # Both managers default to ``use_in_migrations = False`` (Django's base
    # Manager default) — no migration is generated for either.
    objects = models.Manager()
    alive_objects = SoftDeleteManager()

    def delete(self, using=None, keep_parents=False):
        """Soft-delete by setting is_deleted=True instead of removing the row.

        Note: this does NOT fire Django's ``pre_delete`` / ``post_delete``
        signals because the row is updated, not actually deleted.  If you
        need real deletion (and the associated signals), use
        ``hard_delete()`` instead.
        """
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])
        return (1, {self._meta.label: 1})

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete this instance — bypasses soft-delete."""
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        abstract = True


__all__ = ["SoftDeleteModel", "SoftDeleteManager", "SoftDeleteQuerySet"]
