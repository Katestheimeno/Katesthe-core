"""
Reusable abstract model: to keep a history
Path: utils/models/history.py
"""
from django.db import models
from django.utils import timezone
from django.conf import settings


class HistoryModel(models.Model):
    """
    Abstract model to store change history in a JSON field.
    Tracks what changed, when, and by whom (if provided).
    Useful for lightweight auditing without a full audit table.
    """

    # JSON list of change entries (each entry is a dict)
    # Example entry:
    # {
    #   "at": "2025-08-30T10:45:00Z",
    #   "by": "user_id_or_username",
    #   "changes": {"field": {"old": "A", "new": "B"}}
    # }
    history = models.JSONField(default=list, blank=True, editable=False)

    class Meta:
        abstract = True

    # Fields to ignore when tracking changes (override in subclasses if needed)
    HISTORY_IGNORE = ["id", "created_at", "updated_at"]

    def save(self, *args, **kwargs):
        """
        Override save() to automatically track changes.
        - Accepts `changed_by` kwarg for user attribution.
        - Skips ignored fields.
        """
        changed_by = kwargs.pop("changed_by", None)  # custom kwarg

        if self.pk:  # Only check diffs on update
            old = self.__class__.objects.get(pk=self.pk)
            changes = {}

            for field in self._meta.fields:
                name = field.name
                if name in self.HISTORY_IGNORE:
                    continue

                old_val, new_val = getattr(old, name), getattr(self, name)
                if old_val != new_val:
                    changes[name] = {"old": old_val, "new": new_val}

            # Only record if something actually changed
            if changes:
                entry = {
                    "at": timezone.now().isoformat(),
                    "changes": changes,
                }
                if changed_by:
                    # Store either user ID or string (username/email)
                    entry["by"] = (
                        changed_by.pk
                        if hasattr(changed_by, "pk")
                        else str(changed_by)
                    )
                self.history.append(entry)

        super().save(*args, **kwargs)

    # ------------------
    # Convenience methods
    # ------------------

    def last_changes(self):
        """Return the most recent change entry, or None if no history."""
        return self.history[-1] if self.history else None

    def changes_summary(self):
        """
        Return a human-friendly summary of the latest changes.
        Example: "2025-08-30 - user42 changed ['status', 'name']"
        """
        if not self.history:
            return "No changes recorded."
        last = self.last_changes()
        return f"{last['at']} - {last.get('by', 'system')} changed {list(last['changes'].keys())}"

    def all_changes(self):
        """Return the full history as a list of entries."""
        return self.history

    def changes_for_field(self, field_name):
        """
        Get the change history for a specific field.
        Returns a list of {"old": X, "new": Y, "at": timestamp, "by": user}.
        """
        results = []
        for entry in self.history:
            if field_name in entry["changes"]:
                results.append({
                    "old": entry["changes"][field_name]["old"],
                    "new": entry["changes"][field_name]["new"],
                    "at": entry["at"],
                    "by": entry.get("by", "system")
                })
        return results

    def last_changed_by(self):
        """Return the last user/system who made a change."""
        last = self.last_changes()
        return last.get("by") if last else None

