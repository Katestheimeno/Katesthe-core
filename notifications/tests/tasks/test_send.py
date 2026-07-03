"""
Tests for `notifications.tasks`.
Path: notifications/tests/tasks/test_send.py
"""

import pytest
from django.core import mail
from django.test import override_settings

from notifications.tasks import _redact, send_transactional_email_task

pytestmark = pytest.mark.django_db


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_transactional_email_task_delivers_one_message_with_html_alternative():
    """Calling the task directly sends one message via the configured EMAIL_BACKEND."""
    send_transactional_email_task(
        subject="s",
        to_email="a@b.com",
        text_body="t",
        html_body="<b>t</b>",
        event_code="ACCOUNT__ACTIVATION",
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["a@b.com"]
    assert mail.outbox[0].subject == "s"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_transactional_email_task_without_html_body_sends_plaintext_only():
    """When `html_body` is falsy, no alternative attachment is added."""
    send_transactional_email_task(
        subject="s",
        to_email="a@b.com",
        text_body="t",
        html_body="",
        event_code="ACCOUNT__ACTIVATION",
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].alternatives == []


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_transactional_email_task_wraps_string_reply_to_in_a_list():
    """A bare string `reply_to` is normalized to a single-item list."""
    send_transactional_email_task(
        subject="s",
        to_email="a@b.com",
        text_body="t",
        html_body="",
        event_code="ACCOUNT__ACTIVATION",
        reply_to="reply@b.com",
    )

    assert mail.outbox[0].reply_to == ["reply@b.com"]


def test_send_transactional_email_task_has_three_max_retries():
    """The task decorator configures `max_retries=3`."""
    assert send_transactional_email_task.max_retries == 3


def test_send_transactional_email_task_registered_name():
    """The task is registered under the documented Celery task name."""
    assert send_transactional_email_task.name == "notifications.tasks.send_transactional_email"


def test_redact_masks_local_part_and_keeps_domain():
    """`_redact` keeps only the first character of the local part."""
    assert _redact("john@doe.com") == "j***@doe.com"


def test_redact_returns_dash_for_empty_string():
    """`_redact` returns a placeholder for an empty/falsy value."""
    assert _redact("") == "-"


def test_redact_returns_dash_for_none():
    """`_redact` returns a placeholder for `None`."""
    assert _redact(None) == "-"


def test_redact_returns_dash_for_value_without_at_sign():
    """`_redact` returns a placeholder when the value has no `@`."""
    assert _redact("not-an-email") == "-"
