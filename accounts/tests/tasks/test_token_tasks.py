"""
Tests for accounts.tasks.token_tasks.flush_expired_jwt_tokens.
Path: accounts/tests/tasks/test_token_tasks.py
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from accounts.tasks import example_cleanup_task, flush_expired_jwt_tokens
from accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_flush_expired_jwt_tokens_deletes_expired_and_keeps_active_tokens():
    user = UserFactory()
    expired = OutstandingToken.objects.create(
        user=user,
        jti="test-jti-expired",
        token="fake.token.expired",
        created_at=timezone.now() - timedelta(days=10),
        expires_at=timezone.now() - timedelta(days=3),
    )
    active = OutstandingToken.objects.create(
        user=user,
        jti="test-jti-active",
        token="fake.token.active",
        created_at=timezone.now(),
        expires_at=timezone.now() + timedelta(days=7),
    )

    deleted_count = flush_expired_jwt_tokens()

    assert deleted_count == 1
    assert not OutstandingToken.objects.filter(pk=expired.pk).exists()
    assert OutstandingToken.objects.filter(pk=active.pk).exists()


@pytest.mark.django_db
def test_flush_expired_jwt_tokens_cascades_to_blacklisted_token():
    user = UserFactory()
    expired = OutstandingToken.objects.create(
        user=user,
        jti="test-jti-cascade",
        token="fake.token.cascade",
        created_at=timezone.now() - timedelta(days=10),
        expires_at=timezone.now() - timedelta(days=3),
    )
    BlacklistedToken.objects.create(token=expired)

    deleted_count = flush_expired_jwt_tokens()

    # Returned count is OutstandingToken rows only — the cascaded
    # BlacklistedToken row must NOT inflate it (1, not 2).
    assert deleted_count == 1
    assert not OutstandingToken.objects.filter(pk=expired.pk).exists()
    assert not BlacklistedToken.objects.filter(token=expired).exists()


@pytest.mark.django_db
def test_flush_expired_jwt_tokens_returns_zero_when_nothing_expired():
    user = UserFactory()
    OutstandingToken.objects.create(
        user=user,
        jti="test-jti-only-active",
        token="fake.token.only-active",
        created_at=timezone.now(),
        expires_at=timezone.now() + timedelta(days=1),
    )

    deleted_count = flush_expired_jwt_tokens()

    assert deleted_count == 0


def test_flush_expired_jwt_tokens_has_expected_task_name():
    assert flush_expired_jwt_tokens.name == "accounts.tasks.flush_expired_jwt_tokens"


def test_accounts_tasks_package_reexports_both_tasks():
    # The top-level `from accounts.tasks import example_cleanup_task,
    # flush_expired_jwt_tokens` at module scope already proves both names
    # are re-exported by the package `__init__.py`; assert they resolve to
    # the expected registered Celery task names.
    assert example_cleanup_task.name == "accounts.tasks.example_cleanup_task"
    assert flush_expired_jwt_tokens.name == "accounts.tasks.flush_expired_jwt_tokens"
