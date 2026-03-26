"""Utilities for explicit primary-database routing."""

from contextlib import contextmanager

from config.db_router import force_primary_for_request, release_primary_for_request


@contextmanager
def read_from_primary():
    """Scope reads to the primary (read-after-write safe)."""
    force_primary_for_request()
    try:
        yield
    finally:
        release_primary_for_request()


def queryset_on_primary(queryset):
    """Pin an existing queryset to the primary database."""
    return queryset.using("default")
