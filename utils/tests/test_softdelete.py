"""
Tests for the upgraded SoftDeleteModel / SoftDeleteManager / SoftDeleteQuerySet.
Path: utils/tests/test_softdelete.py
"""

import pytest
from django.db import connection, models

from utils.models import SoftDeleteModel, SoftDeleteQuerySet


class SoftDeleteExample(SoftDeleteModel):
    """Concrete, DB-backed model used to exercise manager/queryset behavior."""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "utils"


@pytest.fixture
def sd_table(transactional_db):
    """Create the table for SoftDeleteExample, if it doesn't already exist.

    The ``utils`` app ships no migrations, so Django's test-db bootstrap
    (run_syncdb) auto-creates tables for every model registered under it —
    including this module-level test model — the first time the test
    database is built. Guard the create/delete against that so this fixture
    is idempotent whether or not the table pre-exists.
    """
    table_name = SoftDeleteExample._meta.db_table
    already_exists = table_name in connection.introspection.table_names()
    if not already_exists:
        with connection.schema_editor() as se:
            se.create_model(SoftDeleteExample)
    yield
    if not already_exists:
        with connection.schema_editor() as se:
            se.delete_model(SoftDeleteExample)


@pytest.mark.django_db
class TestSoftDeleteManagers:
    """objects stays unfiltered; alive_objects filters is_deleted=False."""

    def test_objects_returns_all_rows_including_soft_deleted(self, sd_table):
        alive = SoftDeleteExample.objects.create(name="alive")
        dead = SoftDeleteExample.objects.create(name="dead", is_deleted=True)

        all_rows = set(SoftDeleteExample.objects.values_list("pk", flat=True))

        assert all_rows == {alive.pk, dead.pk}

    def test_alive_objects_returns_only_non_deleted_rows(self, sd_table):
        alive = SoftDeleteExample.objects.create(name="alive")
        SoftDeleteExample.objects.create(name="dead", is_deleted=True)

        alive_rows = list(SoftDeleteExample.alive_objects.all())

        assert alive_rows == [alive]


@pytest.mark.django_db
class TestSoftDeleteInstanceDelete:
    """Instance .delete() soft-deletes; .hard_delete() truly removes the row."""

    def test_instance_delete_sets_is_deleted_and_persists_via_update_fields(self, sd_table):
        instance = SoftDeleteExample.objects.create(name="to-delete")

        result = instance.delete()

        instance.refresh_from_db()
        assert instance.is_deleted is True
        assert result == (1, {SoftDeleteExample._meta.label: 1})

    def test_instance_delete_row_present_in_objects_absent_from_alive_objects(self, sd_table):
        instance = SoftDeleteExample.objects.create(name="to-delete")

        instance.delete()

        assert SoftDeleteExample.objects.filter(pk=instance.pk).exists()
        assert not SoftDeleteExample.alive_objects.filter(pk=instance.pk).exists()

    def test_hard_delete_removes_row_from_database(self, sd_table):
        instance = SoftDeleteExample.objects.create(name="to-hard-delete")

        instance.hard_delete()

        assert not SoftDeleteExample.objects.filter(pk=instance.pk).exists()


def _unfiltered_queryset():
    """Build a bare SoftDeleteQuerySet, bypassing manager-level filtering."""
    return SoftDeleteQuerySet(SoftDeleteExample)


@pytest.mark.django_db
class TestSoftDeleteQuerySet:
    """QuerySet-level .alive()/.dead()/.delete()/.hard_delete()."""

    def test_queryset_alive_filters_non_deleted_rows(self, sd_table):
        alive = SoftDeleteExample.objects.create(name="alive")
        SoftDeleteExample.objects.create(name="dead", is_deleted=True)

        assert list(_unfiltered_queryset().alive()) == [alive]

    def test_queryset_dead_filters_deleted_rows(self, sd_table):
        SoftDeleteExample.objects.create(name="alive")
        dead = SoftDeleteExample.objects.create(name="dead", is_deleted=True)

        assert list(_unfiltered_queryset().dead()) == [dead]

    def test_queryset_delete_bulk_soft_deletes_and_returns_count(self, sd_table):
        first = SoftDeleteExample.objects.create(name="one")
        second = SoftDeleteExample.objects.create(name="two")

        result = _unfiltered_queryset().filter(
            pk__in=[first.pk, second.pk]
        ).delete()

        assert result == (2, {SoftDeleteExample._meta.label: 2})
        assert not SoftDeleteExample.alive_objects.filter(
            pk__in=[first.pk, second.pk]
        ).exists()

    def test_queryset_hard_delete_removes_rows(self, sd_table):
        first = SoftDeleteExample.objects.create(name="one")
        second = SoftDeleteExample.objects.create(name="two")

        _unfiltered_queryset().filter(pk__in=[first.pk, second.pk]).hard_delete()

        assert not SoftDeleteExample.objects.filter(
            pk__in=[first.pk, second.pk]
        ).exists()
