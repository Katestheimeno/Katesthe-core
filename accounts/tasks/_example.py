"""
Example Celery task for the accounts app.
Path: accounts/tasks/_example.py
"""

from celery import shared_task

from config.logger import logger


@shared_task(
    name="accounts.tasks.example_cleanup_task",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def example_cleanup_task():
    """Example: delete inactive users older than 30 days. Idempotent by design."""
    from datetime import timedelta
    from django.utils import timezone
    from django.contrib.auth import get_user_model

    User = get_user_model()
    cutoff = timezone.now() - timedelta(days=30)
    # Idempotent: filtering by state means re-running deletes nothing new.
    qs = User.objects.filter(is_active=False, date_joined__lt=cutoff)
    count = qs.count()
    qs.delete()
    logger.bind(deleted=count).info("accounts.example_cleanup_task.done")
    return count
