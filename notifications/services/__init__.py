"""
Services (write/orchestration) package for the notifications app.
Path: notifications/services/__init__.py
"""

from .transactional_email import send_transactional_email

__all__ = [
    "send_transactional_email",
]
