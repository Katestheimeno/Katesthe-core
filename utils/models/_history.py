"""
History Model and Additional Handy Abstract Models
Path: utils/models/
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

imports = []

imports += ["HistoryModel"]

# ==================== ENHANCED HISTORY MODEL ====================

class HistoryJSONEncoder(DjangoJSONEncoder):
    """Custom JSON encoder to handle more data types in history"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if hasattr(obj, 'pk'):
            return {'_model': obj.__class__.__name__, '_pk': obj.pk}
        return super().default(obj)


class HistoryManager(models.Manager):
    """Manager for models with history tracking"""
    
    def with_recent_changes(self, days=30):
        """Filter objects that have been modified in the last N days"""
        since = timezone.now() - timedelta(days=days)
        return self.filter(updated_at__gte=since)
    
    def changed_by_user(self, user):
        """Filter objects that were changed by a specific user"""
        return self.filter(history__contains=[{'by': user.pk}])


class HistoryModel(models.Model):
    """
    Abstract model to store detailed change history.
    
    Improvements over basic HistoryModel:
    - Better data type handling
    - Compression for large histories
    - Field-level metadata
    - Change categories/tags
    - Bulk change detection
    - Performance optimizations
    - Query helpers
    """

    history = models.JSONField(
        default=list, 
        blank=True, 
        editable=False,
        encoder=HistoryJSONEncoder,
        help_text="JSON array of change history entries"
    )
    
    # Performance optimization: store last change timestamp separately
    last_changed_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='%(class)s_last_changes',
        editable=False
    )
    
    # History metadata
    history_version = models.PositiveIntegerField(default=1, editable=False)
    history_compressed = models.BooleanField(default=False, editable=False)

    objects = HistoryManager()

    class Meta:
        abstract = True

    # Configuration (override in subclasses)
    HISTORY_IGNORE = ["id", "created_at", "updated_at", "history", "last_changed_at", "last_changed_by"]
    HISTORY_MAX_ENTRIES = 100  # Compress when exceeded
    HISTORY_TRACK_RELATIONS = True  # Track FK/M2M changes
    HISTORY_CATEGORIES = {
        'status_change': ['status', 'state', 'is_active'],
        'content_update': ['title', 'description', 'content'],
        'metadata': ['tags', 'category', 'priority'],
    }

    def save(self, *args, **kwargs):
        """Save with better change tracking"""
        changed_by = kwargs.pop("changed_by", None)
        change_category = kwargs.pop("change_category", None)
        change_note = kwargs.pop("change_note", None)
        bulk_update = kwargs.pop("bulk_update", False)

        if self.pk and not bulk_update:
            self._track_changes(changed_by, change_category, change_note)
        
        super().save(*args, **kwargs)

    def _track_changes(self, changed_by=None, category=None, note=None):
        """Internal method to track changes with enhanced features"""
        try:
            old = self.__class__.objects.get(pk=self.pk)
        except self.__class__.DoesNotExist:
            return

        changes = {}
        field_metadata = {}

        # Track field changes
        for field in self._meta.fields:
            if field.name in self.HISTORY_IGNORE:
                continue

            old_val = self._serialize_field_value(field, getattr(old, field.name))
            new_val = self._serialize_field_value(field, getattr(self, field.name))

            if old_val != new_val:
                changes[field.name] = {"old": old_val, "new": new_val}
                field_metadata[field.name] = {
                    "type": field.__class__.__name__,
                    "verbose_name": str(field.verbose_name)
                }

        # Track relation changes if enabled
        if self.HISTORY_TRACK_RELATIONS:
            self._track_relation_changes(old, changes, field_metadata)

        if changes:
            self._add_history_entry(changes, field_metadata, changed_by, category, note)

    def _serialize_field_value(self, field, value):
        """Serialize field values for comparison"""
        if value is None:
            return None
        
        if isinstance(field, models.ForeignKey) and value:
            return {"pk": value.pk, "str": str(value)}
        
        if isinstance(field, (models.DateTimeField, models.DateField, models.TimeField)):
            return value.isoformat() if value else None
            
        if isinstance(field, models.DecimalField):
            return str(value) if value is not None else None
            
        if isinstance(field, models.JSONField):
            return value  # Already JSON serializable
            
        return value

    def _track_relation_changes(self, old_instance, changes, metadata):
        """Track changes in foreign key and many-to-many relationships"""
        # This is a simplified version - full implementation would handle M2M
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name not in self.HISTORY_IGNORE:
                old_val = getattr(old_instance, field.name)
                new_val = getattr(self, field.name)
                
                if old_val != new_val:
                    changes[field.name] = {
                        "old": {"pk": old_val.pk, "str": str(old_val)} if old_val else None,
                        "new": {"pk": new_val.pk, "str": str(new_val)} if new_val else None,
                    }
                    metadata[field.name] = {
                        "type": "ForeignKey",
                        "related_model": field.related_model.__name__
                    }

    def _add_history_entry(self, changes, metadata, changed_by=None, category=None, note=None):
        """Add a new entry to history with metadata"""
        entry = {
            "timestamp": timezone.now().isoformat(),
            "changes": changes,
            "metadata": metadata,
            "version": self.history_version
        }

        if changed_by:
            entry["by"] = {
                "pk": changed_by.pk if hasattr(changed_by, "pk") else None,
                "username": getattr(changed_by, "username", str(changed_by))
            }

        if category or self._detect_change_category(changes):
            entry["category"] = category or self._detect_change_category(changes)

        if note:
            entry["note"] = note

        self.history.append(entry)
        self.last_changed_at = timezone.now()
        if changed_by and hasattr(changed_by, "pk"):
            self.last_changed_by = changed_by
        self.history_version += 1

        # Compress history if it gets too large
        if len(self.history) > self.HISTORY_MAX_ENTRIES:
            self._compress_history()

    def _detect_change_category(self, changes):
        """Auto-detect change category based on fields changed"""
        for category, fields in self.HISTORY_CATEGORIES.items():
            if any(field in changes for field in fields):
                return category
        return "general"

    def _compress_history(self):
        """Compress old history entries to save space"""
        if len(self.history) <= self.HISTORY_MAX_ENTRIES:
            return

        # Keep recent entries, compress older ones
        recent = self.history[-self.HISTORY_MAX_ENTRIES//2:]
        old_entries = self.history[:-self.HISTORY_MAX_ENTRIES//2]
        
        # Create compressed summary
        compressed_summary = {
            "compressed_at": timezone.now().isoformat(),
            "entries_count": len(old_entries),
            "date_range": {
                "from": old_entries[0]["timestamp"] if old_entries else None,
                "to": old_entries[-1]["timestamp"] if old_entries else None
            },
            "summary": self._create_change_summary(old_entries)
        }

        self.history = [compressed_summary] + recent
        self.history_compressed = True

    def _create_change_summary(self, entries):
        """Create a summary of compressed entries"""
        field_changes = {}
        users = set()
        categories = set()

        for entry in entries:
            for field in entry.get("changes", {}):
                field_changes[field] = field_changes.get(field, 0) + 1
            
            if "by" in entry:
                users.add(entry["by"].get("username", "unknown"))
            
            if "category" in entry:
                categories.add(entry["category"])

        return {
            "most_changed_fields": sorted(field_changes.items(), key=lambda x: x[1], reverse=True)[:5],
            "unique_users": list(users),
            "categories": list(categories)
        }

    # Enhanced query methods
    def get_changes_since(self, timestamp):
        """Get all changes since a specific timestamp"""
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        
        return [entry for entry in self.history 
                if entry.get("timestamp", "") > timestamp]

    def get_changes_by_user(self, user):
        """Get changes made by a specific user"""
        user_pk = user.pk if hasattr(user, "pk") else None
        username = getattr(user, "username", str(user))
        
        return [entry for entry in self.history 
                if entry.get("by", {}).get("pk") == user_pk or 
                   entry.get("by", {}).get("username") == username]

    def get_changes_by_category(self, category):
        """Get changes by category"""
        return [entry for entry in self.history 
                if entry.get("category") == category]

    def get_field_history(self, field_name):
        """Get complete history for a specific field"""
        field_history = []
        for entry in self.history:
            if field_name in entry.get("changes", {}):
                field_history.append({
                    "timestamp": entry["timestamp"],
                    "old_value": entry["changes"][field_name]["old"],
                    "new_value": entry["changes"][field_name]["new"],
                    "changed_by": entry.get("by"),
                    "note": entry.get("note")
                })
        return field_history


__all__ = imports