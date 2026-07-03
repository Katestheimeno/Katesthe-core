"""
Generic processor for transactional outbox entries.
Path: utils/outbox.py
"""

from django.utils import timezone

__all__ = ["process_outbox_entry"]


def process_outbox_entry(entry, publisher_fn):
    """Generic processor: call publisher_fn(entry); mark processed/failed. Re-raises on failure."""
    try:
        publisher_fn(entry)
    except Exception as exc:
        entry.status = entry.Status.FAILED
        entry.error_message = str(exc)
        entry.processed_at = timezone.now()
        entry.save(update_fields=["status", "error_message", "processed_at"])
        raise
    else:
        entry.status = entry.Status.PROCESSED
        entry.error_message = ""
        entry.processed_at = timezone.now()
        entry.save(update_fields=["status", "error_message", "processed_at"])
