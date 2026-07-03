"""
Abstract transactional outbox model.
Path: utils/models/_outbox.py
"""

from django.db import models

__all__ = ["BaseOutbox"]


class BaseOutbox(models.Model):
    """
    Abstract base for the transactional outbox pattern.

    Concrete subclasses persist an outbox row inside the same DB
    transaction as the write that triggers an external side effect
    (webhook, third-party publish, ...). A worker/task later processes
    pending rows via `utils.outbox.process_outbox_entry`.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        abstract = True
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} [{self.status}]"
