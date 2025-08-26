from celery.schedules import crontab
imports = []

imports += ["CELERY_BEAT_SCHEDULE"]
CELERY_BEAT_SCHEDULE = {
    # every 1 minute
    # 'say-hello-every-minute': {
    #     'task': 'appointments.tasks.my_task',
    #     'schedule': 60.0,
    #     'args': ("DevMozach",)
    # },
    # # every day at 8:00 AM
    # 'daily-task': {
    #     'task': 'appointments.tasks.daily_task',
    #     'schedule': crontab(hour=8, minute=0),
    #     'args': ()
    # },
    # # every Monday at 9:30 AM
    # 'weekly-task': {
    #     'task': 'appointments.tasks.weekly_task',
    #     'schedule': crontab(hour=9, minute=30, day_of_week=1),
    #     'args': ()
    # },
}
imports += ["CELERY_TASK_QUEUES"]

CELERY_TASK_QUEUES = {
    # 'default': {
    #     'exchange': 'default',
    #     'routing_key': 'default',
    # },
    # 'emails': {
    #     'exchange': 'emails',
    #     'routing_key': 'emails',
    # },
}

imports += ["CELERY_TASK_ROUTES"]
CELERY_TASK_ROUTES = {
    # 'appointments.tasks.send_email': {'queue': 'emails'},
    # 'appointments.tasks.my_task': {'queue': 'default'},
}


__all__ = imports
