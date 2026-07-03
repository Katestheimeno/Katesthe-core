"""
Celery tasks for the notifications app.
Path: notifications/tasks.py

`send_transactional_email_task` is the sole delivery mechanism for
transactional emails: it sends through Django's standard `EMAIL_BACKEND`
(no OneSignal / Ably / domain-specific side channels).
"""

from celery import shared_task

from config.logger import logger


def _redact(email):
    """Redact an email address for safe logging (keep first char of local part)."""
    if not email or "@" not in email:
        return "-"
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


@shared_task(
    name="notifications.tasks.send_transactional_email",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    ignore_result=True,
)
def send_transactional_email_task(*, subject, to_email, text_body, html_body, event_code, from_email=None, reply_to=None):
    """Send a transactional email via Django's `EMAIL_BACKEND`."""
    from django.core.mail import EmailMultiAlternatives

    reply_to = [reply_to] if isinstance(reply_to, str) else reply_to

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[to_email],
        reply_to=reply_to,
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    msg.send()

    logger.bind(event_code=event_code, to=_redact(to_email)).info("notifications.email.sent")
