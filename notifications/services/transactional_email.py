"""
Transactional email dispatch service.
Path: notifications/services/transactional_email.py

Maps an internal `event_code` to an email template stem, renders the
body, and enqueues delivery through `notifications.tasks.send_transactional_email_task`
via `transaction.on_commit` so the email is only ever sent after the
triggering DB transaction has actually committed.

This service never raises into the caller: any failure (unknown event,
missing recipient, missing template, unexpected error) is logged and the
function returns `None`.
"""

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string

from config.logger import logger

from notifications.tasks import send_transactional_email_task

# Event code -> template stem (under `notifications/templates/`).
# Only the stems registered here are expected to have a matching template;
# a registered event whose template is missing is handled gracefully
# (logged, not raised).
_EVENT_REGISTRY = {
    "ACCOUNT__ACTIVATION": "emails/activation",
    "ACCOUNT__PASSWORD_RESET": "emails/password_reset",
}

# Event code -> subject line. Falls back to a generic subject built from
# the project name and event code when the event has no dedicated entry.
_SUBJECTS = {
    "ACCOUNT__ACTIVATION": "Activate your account",
    "ACCOUNT__PASSWORD_RESET": "Reset your password",
}


def _resolve_recipient_email(recipient):
    """Return an email address for `recipient`, or `None` if it cannot be resolved."""
    if isinstance(recipient, str):
        return recipient or None
    email = getattr(recipient, "email", None)
    return email or None


def send_transactional_email(*, event_code, recipient, context=None, from_email=None, reply_to=None):
    """Render and enqueue a transactional email for `event_code`.

    Never raises into the caller — any failure is logged and the function
    returns `None`.
    """
    try:
        email = _resolve_recipient_email(recipient)
        if not email:
            logger.bind(event_code=event_code).warning("notifications.email.no_recipient")
            return None

        template_stem = _EVENT_REGISTRY.get(event_code)
        if not template_stem:
            logger.bind(event_code=event_code).warning("notifications.email.unknown_event")
            return None

        project_name = getattr(settings, "PROJECT_NAME", "App")
        render_context = {"project_name": project_name, **(context or {})}

        subject = _SUBJECTS.get(event_code, f"{project_name} — {event_code}")

        try:
            html_body = render_to_string(f"{template_stem}.html", render_context)
        except Exception:
            logger.bind(event_code=event_code).warning("notifications.email.template_missing")
            return None

        text_body = (context or {}).get("text_body") or f"{subject}"

        transaction.on_commit(
            lambda: send_transactional_email_task.delay(
                subject=subject,
                to_email=email,
                text_body=text_body,
                html_body=html_body,
                event_code=event_code,
                from_email=from_email,
                reply_to=reply_to,
            )
        )
        return None
    except Exception:
        logger.bind(event_code=event_code).warning("notifications.email.dispatch_failed")
        return None
