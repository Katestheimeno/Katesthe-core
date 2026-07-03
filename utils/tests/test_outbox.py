"""
Tests for utils.models.BaseOutbox and utils.outbox.process_outbox_entry.
Path: utils/tests/test_outbox.py
"""

from utils.models import BaseOutbox
from utils.outbox import process_outbox_entry


class TestBaseOutboxStructure:
    """Structural assertions on the abstract BaseOutbox model (no DB)."""

    def test_base_outbox_declares_expected_fields(self):
        """BaseOutbox exposes exactly the six specified concrete fields."""
        field_names = {f.name for f in BaseOutbox._meta.get_fields()}
        expected = {"event_type", "payload", "status", "created_at", "processed_at", "error_message"}

        assert field_names == expected

    def test_base_outbox_is_abstract(self):
        """BaseOutbox is declared abstract and generates no migration/table."""
        assert BaseOutbox._meta.abstract is True

    def test_base_outbox_status_choices_values(self):
        """Status enum exposes pending/processed/failed string values."""
        assert BaseOutbox.Status.PENDING == "pending"
        assert BaseOutbox.Status.PROCESSED == "processed"
        assert BaseOutbox.Status.FAILED == "failed"


class _FakeOutboxEntry:
    """Lightweight stand-in for a BaseOutbox row, avoiding a concrete DB model."""

    Status = BaseOutbox.Status

    def __init__(self):
        self.status = self.Status.PENDING
        self.error_message = ""
        self.processed_at = None
        self.save_calls = []

    def save(self, update_fields=None):
        self.save_calls.append(update_fields)


class TestProcessOutboxEntry:
    """Behavior tests for process_outbox_entry() using a fake entry object."""

    def test_process_outbox_entry_marks_processed_on_success(self):
        """A publisher_fn that succeeds marks the entry as processed."""
        entry = _FakeOutboxEntry()

        process_outbox_entry(entry, lambda e: None)

        assert entry.status == BaseOutbox.Status.PROCESSED
        assert entry.processed_at is not None
        assert entry.error_message == ""
        assert len(entry.save_calls) == 1

    def test_process_outbox_entry_marks_failed_and_reraises_on_failure(self):
        """A publisher_fn that raises marks the entry failed and re-raises the exception."""
        import pytest

        entry = _FakeOutboxEntry()

        def _boom(e):
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            process_outbox_entry(entry, _boom)

        assert entry.status == BaseOutbox.Status.FAILED
        assert entry.error_message == "boom"
        assert entry.processed_at is not None
        assert len(entry.save_calls) == 1
