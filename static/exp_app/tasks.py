"""
Celery tasks for this app.
Follow the standard pattern: idempotent, auto-retrying, enqueued from a service via transaction.on_commit.
"""
# from celery import shared_task
# from config.logger import logger
#
# @shared_task(
#     name="<app_label>.tasks.example_task",
#     autoretry_for=(Exception,),
#     max_retries=3,
#     retry_backoff=True,
#     retry_backoff_max=300,
#     retry_jitter=True,
# )
# def example_task():
#     """Idempotent by design. Persist correlation state in the DB, not in task args."""
#     logger.info("<app_label>.example_task.done")
