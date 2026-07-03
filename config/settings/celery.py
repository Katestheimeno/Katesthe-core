"""
Celery configuration placeholders: beat schedule, queues, and routes.
Path: config/settings/celery.py
"""

from celery.schedules import crontab

# We'll collect all exported configs in `imports` 
# and expose them via __all__ at the bottom
imports = []


# -----------------------------------------------------------------------------
# CELERY BEAT SCHEDULE
# -----------------------------------------------------------------------------
# This defines periodic tasks that will be executed automatically 
# at fixed intervals (like cron jobs).
imports += ["CELERY_BEAT_SCHEDULE"]

CELERY_BEAT_SCHEDULE = {
    "example-cleanup": {
        "task": "accounts.tasks.example_cleanup_task",
        "schedule": 86400,  # daily, seconds
    },
}


# -----------------------------------------------------------------------------
# CELERY TASK QUEUES
# -----------------------------------------------------------------------------
# Queues allow you to send certain tasks to specific workers.
# Example: heavy tasks like sending emails could go to a dedicated "emails" queue.
imports += ["CELERY_TASK_QUEUES"]

CELERY_TASK_QUEUES = {
    # Default queue (all tasks go here unless specified otherwise)
    # 'default': {
    #     'exchange': 'default',         # exchange name (think routing hub)
    #     'routing_key': 'default',      # used to match with routes
    # },
    
    # Dedicated queue for email tasks
    # 'emails': {
    #     'exchange': 'emails',
    #     'routing_key': 'emails',
    # },
}


# -----------------------------------------------------------------------------
# CELERY TASK ROUTES
# -----------------------------------------------------------------------------
# Routing rules: tells Celery which task should go to which queue.
imports += ["CELERY_TASK_ROUTES"]

CELERY_TASK_ROUTES = {
    # Example: all "send_email" tasks go to the "emails" queue
    # 'appointments.tasks.send_email': {'queue': 'emails'},
    
    # Example: custom task goes to the default queue
    # 'appointments.tasks.my_task': {'queue': 'default'},
}


# -----------------------------------------------------------------------------
# CELERY TASK SECURITY (SERIALIZATION)
# -----------------------------------------------------------------------------
# Restrict Celery to JSON only — avoids pickle-based deserialization risks.
imports += ["CELERY_TASK_SERIALIZER", "CELERY_RESULT_SERIALIZER", "CELERY_ACCEPT_CONTENT"]

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]


# -----------------------------------------------------------------------------
# CELERY WORKER TUNING
# -----------------------------------------------------------------------------
# Recycle workers periodically to avoid memory leaks; cap memory per child.
imports += ["CELERY_WORKER_MAX_TASKS_PER_CHILD", "CELERY_WORKER_MAX_MEMORY_PER_CHILD"]

CELERY_WORKER_MAX_TASKS_PER_CHILD = 500
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 256_000  # 256MB


# -----------------------------------------------------------------------------
# CELERY TASK TIME LIMITS
# -----------------------------------------------------------------------------
# Hard limit kills the task; soft limit raises SoftTimeLimitExceeded first.
imports += ["CELERY_TASK_TIME_LIMIT", "CELERY_TASK_SOFT_TIME_LIMIT"]

CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540


# -----------------------------------------------------------------------------
# CELERY WORKER PREFETCH
# -----------------------------------------------------------------------------
# Prefetch 1 task at a time — fairer distribution for long-running tasks.
imports += ["CELERY_WORKER_PREFETCH_MULTIPLIER"]

CELERY_WORKER_PREFETCH_MULTIPLIER = 1


# -----------------------------------------------------------------------------
# EXPORT SETTINGS
# -----------------------------------------------------------------------------
# __all__ makes these settings available when imported elsewhere.
__all__ = imports

