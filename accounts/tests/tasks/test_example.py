"""
Tests for accounts.tasks.example_cleanup_task.
Path: accounts/tests/tasks/test_example.py
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.tasks import example_cleanup_task
from accounts.tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
def test_example_cleanup_task_deletes_old_inactive_users_and_keeps_recent_active_user():
    old_cutoff = timezone.now() - timedelta(days=40)
    UserFactory(is_active=False, date_joined=old_cutoff)
    UserFactory(is_active=False, date_joined=old_cutoff)
    recent_active_user = UserFactory(is_active=True, date_joined=timezone.now())

    deleted_count = example_cleanup_task()

    assert deleted_count == 2
    assert User.objects.count() == 1
    assert User.objects.filter(pk=recent_active_user.pk).exists()


@pytest.mark.django_db
def test_example_cleanup_task_is_idempotent_on_second_run():
    old_cutoff = timezone.now() - timedelta(days=40)
    UserFactory(is_active=False, date_joined=old_cutoff)

    first_run_deleted_count = example_cleanup_task()
    second_run_deleted_count = example_cleanup_task()

    assert first_run_deleted_count == 1
    assert second_run_deleted_count == 0


def test_example_cleanup_task_has_expected_retry_configuration():
    assert example_cleanup_task.max_retries == 3
    assert example_cleanup_task.name == "accounts.tasks.example_cleanup_task"
