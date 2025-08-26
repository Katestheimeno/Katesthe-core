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
    # Example: run every 1 minute
    # 'say-hello-every-minute': {
    #     'task': 'appointments.tasks.my_task',  # path to your Celery task
    #     'schedule': 60.0,                      # seconds (float or int)
    #     'args': ("DevMozach",),                # optional arguments passed to the task
    # },
    
    # Example: run every day at 8:00 AM
    # 'daily-task': {
    #     'task': 'appointments.tasks.daily_task',
    #     'schedule': crontab(hour=8, minute=0),  # crontab gives more control
    #     'args': (),                             # can be empty
    # },
    
    # Example: run every Monday at 9:30 AM
    # 'weekly-task': {
    #     'task': 'appointments.tasks.weekly_task',
    #     'schedule': crontab(hour=9, minute=30, day_of_week=1),
    #     'args': (),
    # },
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
# EXPORT SETTINGS
# -----------------------------------------------------------------------------
# __all__ makes these settings available when imported elsewhere.
__all__ = imports

