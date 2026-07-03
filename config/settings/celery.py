"""
Celery configuration placeholders: beat schedule, queues, and routes.
Path: config/settings/celery.py
"""

from celery.schedules import crontab
from kombu import Queue

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
    "keep-warm": {
        "task": "utils.tasks.keep_warm",
        "schedule": 240.0,  # every 4 minutes
    },
    "flush-expired-jwt-tokens": {
        "task": "accounts.tasks.flush_expired_jwt_tokens",
        "schedule": 86400,  # daily; task provided by the auth-core plan (routed by name)
    },
}


# -----------------------------------------------------------------------------
# CELERY TASK QUEUES
# -----------------------------------------------------------------------------
# Three queues split by latency requirements:
#   - realtime: latency-sensitive, WebSocket-triggered work (<1s SLA)
#   - default:  notifications, membership, stats, general work
#   - slow:     bulk operations, heavy analytics, nightly maintenance
#
# Run workers per queue:
#   celery -A config.celery.app worker -Q realtime --concurrency=4
#   celery -A config.celery.app worker -Q default  --concurrency=8
#   celery -A config.celery.app worker -Q slow     --concurrency=2
#
# Or a single worker consuming all:
#   celery -A config.celery.app worker -Q realtime,default,slow --concurrency=8
imports += ["CELERY_TASK_DEFAULT_QUEUE", "CELERY_TASK_QUEUES"]

CELERY_TASK_DEFAULT_QUEUE = "default"

CELERY_TASK_QUEUES = (
    Queue("realtime", routing_key="realtime"),
    Queue("default", routing_key="default"),
    Queue("slow", routing_key="slow"),
)


# -----------------------------------------------------------------------------
# CELERY TASK ROUTES
# -----------------------------------------------------------------------------
# Routing rules: tells Celery which task should go to which queue.
imports += ["CELERY_TASK_ROUTES"]

CELERY_TASK_ROUTES = {
    # Nightly maintenance → slow queue (don't block default workers)
    "accounts.tasks.flush_expired_jwt_tokens": {"queue": "slow"},

    # Example (no plan creates this task yet — keep commented until it exists):
    # "accounts.tasks.process_permanent_deletions": {"queue": "slow"},

    # Everything else → default (projects add routes as they add tasks).
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

