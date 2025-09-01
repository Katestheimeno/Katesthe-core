"""
Cache suffix
"""

import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

imports = []

imports += ["CacheModel"]


class CacheModel(models.Model):
    """
    Abstract model for cached data with TTL and invalidation
    """
    cache_key = models.CharField(max_length=255, unique=True, editable=False)
    cached_data = models.JSONField(default=dict)
    cached_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    cache_version = models.CharField(max_length=50, default="1.0")
    
    class Meta:
        abstract = True

    def is_expired(self):
        """Check if cache is expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def invalidate(self):
        """Mark cache as expired"""
        self.expires_at = timezone.now()
        self.save()


__all__ = imports