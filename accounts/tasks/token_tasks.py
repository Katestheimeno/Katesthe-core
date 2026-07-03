"""
Periodic JWT token housekeeping tasks.
Path: accounts/tasks/token_tasks.py
"""

from celery import shared_task

from config.logger import logger


@shared_task(
    name="accounts.tasks.flush_expired_jwt_tokens",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    time_limit=60,
    soft_time_limit=50,
    ignore_result=True,
)
def flush_expired_jwt_tokens():
    """
    Delete expired outstanding JWT tokens and their blacklist entries.
    Equivalent to: python manage.py flushexpiredtokens
    """
    from django.utils import timezone
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

    qs = OutstandingToken.objects.filter(expires_at__lt=timezone.now())
    # delete() returns (total_rows_including_cascades, per_model_counts).
    # The first value also counts cascaded BlacklistedToken rows, so report
    # per-model counts and return the OutstandingToken count only.
    _total, per_model = qs.delete()
    outstanding_deleted = per_model.get("token_blacklist.OutstandingToken", 0)
    blacklist_deleted = per_model.get("token_blacklist.BlacklistedToken", 0)
    logger.bind(
        outstanding_deleted=outstanding_deleted,
        blacklist_deleted=blacklist_deleted,
    ).info("jwt.flush_expired_tokens")
    return outstanding_deleted
