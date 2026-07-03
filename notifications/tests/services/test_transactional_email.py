"""
Tests for `notifications.services.transactional_email`.
Path: notifications/tests/services/test_transactional_email.py
"""

import pytest
from django.core import mail
from django.test import override_settings

from notifications.services import send_transactional_email

pytestmark = pytest.mark.django_db


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_transactional_email_happy_path_lands_one_message_in_outbox(
    user, django_capture_on_commit_callbacks
):
    """A known event with a resolvable recipient renders + enqueues + sends one email."""
    with django_capture_on_commit_callbacks(execute=True):
        send_transactional_email(
            event_code="ACCOUNT__ACTIVATION",
            recipient=user,
            context={"foo": "bar"},
        )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_transactional_email_with_string_recipient_sends(
    django_capture_on_commit_callbacks,
):
    """A bare email string is resolved as the recipient and the email is sent."""
    with django_capture_on_commit_callbacks(execute=True):
        send_transactional_email(event_code="ACCOUNT__ACTIVATION", recipient="a@b.com")

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["a@b.com"]


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_transactional_email_unknown_event_does_not_send_or_raise(
    user, django_capture_on_commit_callbacks
):
    """An unregistered event code is logged and skipped without raising."""
    with django_capture_on_commit_callbacks(execute=True):
        send_transactional_email(event_code="NOPE__X", recipient=user)

    assert mail.outbox == []


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_transactional_email_with_no_recipient_does_not_send_or_raise(
    django_capture_on_commit_callbacks,
):
    """A `None` recipient cannot be resolved to an email; no send, no raise."""
    with django_capture_on_commit_callbacks(execute=True):
        send_transactional_email(event_code="ACCOUNT__ACTIVATION", recipient=None)

    assert mail.outbox == []


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_transactional_email_with_recipient_missing_email_attribute_does_not_send(
    django_capture_on_commit_callbacks,
):
    """An object without a usable `.email` attribute resolves to no recipient."""
    class NoEmail:
        pass

    with django_capture_on_commit_callbacks(execute=True):
        send_transactional_email(event_code="ACCOUNT__ACTIVATION", recipient=NoEmail())

    assert mail.outbox == []


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_transactional_email_template_missing_does_not_send_or_raise(
    user, django_capture_on_commit_callbacks
):
    """A registered event whose template is missing is logged and skipped."""
    from notifications.services import transactional_email as svc

    original_registry = svc._EVENT_REGISTRY
    svc._EVENT_REGISTRY = {**original_registry, "ACCOUNT__ACTIVATION": "emails/does_not_exist"}
    try:
        with django_capture_on_commit_callbacks(execute=True):
            send_transactional_email(event_code="ACCOUNT__ACTIVATION", recipient=user)
    finally:
        svc._EVENT_REGISTRY = original_registry

    assert mail.outbox == []
