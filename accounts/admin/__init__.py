"""
Admin registrations for the accounts app.
Path: accounts/admin/__init__.py
"""

from ._user import *

from django.contrib import admin
from unfold.admin import ModelAdmin
from django.contrib.auth.models import Group
from django_celery_beat.models import (
    PeriodicTask, IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule
)

# --- AUTH ---
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    pass


# --- CELERY BEAT ---
models_to_unfold = [
    PeriodicTask,
    IntervalSchedule,
    CrontabSchedule,
    SolarSchedule,
    ClockedSchedule,
]

for model in models_to_unfold:
    admin.site.unregister(model)

    @admin.register(model)
    class GenericUnfoldAdmin(ModelAdmin):
        pass
