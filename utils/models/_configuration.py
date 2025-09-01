"""
Configuration suffix
"""

imports = []

imports += ["ConfigurationModel"]

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



class ConfigurationModel(models.Model):
    """
    Abstract model for application configuration settings
    """
    key = models.CharField(max_length=255, unique=True)
    value = models.JSONField(default=dict)
    data_type = models.CharField(
        max_length=20,
        choices=[
            ('string', 'String'),
            ('integer', 'Integer'),
            ('float', 'Float'),
            ('boolean', 'Boolean'),
            ('json', 'JSON'),
            ('list', 'List'),
        ],
        default='string'
    )
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False)  # For passwords, API keys, etc.
    
    class Meta:
        abstract = True

    def get_typed_value(self):
        """Return value converted to appropriate type"""
        if self.data_type == 'integer':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        elif self.data_type == 'boolean':
            return bool(self.value)
        elif self.data_type in ['json', 'list']:
            return self.value
        else:
            return str(self.value)


__all__ = imports