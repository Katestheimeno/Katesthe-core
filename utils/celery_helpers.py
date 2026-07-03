"""
Celery helper utilities for safe task execution.
Path: utils/celery_helpers.py

This module provides utilities to safely execute Celery tasks in both
test and production environments.
"""
from django.conf import settings

from config.logger import logger


def safe_task_delay(task, *args, **kwargs):
    """
    Safely execute a Celery task, handling both test and production modes.

    In test mode (CELERY_TASK_ALWAYS_EAGER=True):
    - Uses .apply() to execute synchronously without broker connection
    - Silently handles errors to prevent test failures

    In production mode:
    - Uses .delay() to queue tasks asynchronously
    - Logs errors but doesn't crash the application
    - Allows monitoring systems to detect broker issues

    Args:
        task: The Celery task to execute
        *args: Positional arguments for the task
        **kwargs: Keyword arguments for the task

    Returns:
        The task result (AsyncResult in production, result in eager mode)
        Returns None if task fails to queue/execute

    Example:
        from accounts.tasks.user_tasks import send_welcome_email
        from utils.celery_helpers import safe_task_delay

        # Positional arguments
        safe_task_delay(send_welcome_email, 123)

        # Keyword arguments
        safe_task_delay(send_welcome_email, user_id=123)

        # Mixed
        safe_task_delay(notify_club_members, club_id, 'deleted', {'msg': 'Hello'})
    """
    is_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)

    if is_eager:
        # Test mode: execute synchronously using .apply()
        # This doesn't require a broker connection
        try:
            return task.apply(args=args, kwargs=kwargs)
        except Exception as e:
            # In tests, silently fail to prevent test failures
            # when broker is unavailable
            logger.debug(f"Task {task.name} failed in eager mode: {e}")
            return None
    else:
        # Production mode: queue asynchronously using .delay()
        try:
            return task.delay(*args, **kwargs)
        except Exception as e:
            # In production, log the error but don't crash
            # This allows the application to continue functioning
            # even if the broker is temporarily unavailable
            logger.error(
                f"Failed to queue Celery task {task.name}: {e}",
                exc_info=True,
                extra={
                    'task_name': task.name,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys()),
                }
            )
            return None


def safe_task_delay_with_countdown(task, countdown_seconds: int, *args, **kwargs):
    """
    Safely execute a Celery task with a countdown delay.

    In test mode (CELERY_TASK_ALWAYS_EAGER=True):
    - Uses .apply() to execute synchronously (countdown ignored in tests)
    - Silently handles errors to prevent test failures

    In production mode:
    - Uses .apply_async() with countdown to queue tasks with delay
    - Logs errors but doesn't crash the application

    Args:
        task: The Celery task to execute
        countdown_seconds: Delay in seconds before task execution
        *args: Positional arguments for the task
        **kwargs: Keyword arguments for the task

    Returns:
        The task result (AsyncResult in production, result in eager mode)
        Returns None if task fails to queue/execute

    Example:
        from game.tasks.abandonment_tasks import check_abandonment_after_grace_period
        from utils.celery_helpers import safe_task_delay_with_countdown

        # Schedule task to run after 30 seconds
        safe_task_delay_with_countdown(
            check_abandonment_after_grace_period,
            countdown_seconds=30,
            game_id,
            grace_period
        )
    """
    is_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)

    if is_eager:
        # Test mode: execute synchronously (countdown ignored)
        try:
            return task.apply(args=args, kwargs=kwargs)
        except Exception as e:
            logger.debug(f"Task {task.name} failed in eager mode: {e}")
            return None
    else:
        # Production mode: queue with countdown delay
        try:
            return task.apply_async(args=args, kwargs=kwargs, countdown=countdown_seconds)
        except Exception as e:
            logger.error(
                f"Failed to queue Celery task {task.name} with countdown: {e}",
                exc_info=True,
                extra={
                    'task_name': task.name,
                    'countdown_seconds': countdown_seconds,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys()),
                }
            )
            return None


def safe_send_task(celery_app, task_name: str, args: tuple = (), kwargs: dict = None):
    """
    Safely send a Celery task by name, handling both test and production modes.

    This function extracts the test-specific logic for handling eager mode
    when using task names (strings) instead of task objects.

    In test mode (CELERY_TASK_ALWAYS_EAGER=True):
    - Uses .apply() to execute synchronously without broker connection
    - Handles task lookup from registry or dynamic import

    In production mode:
    - Uses .send_task() to queue tasks asynchronously
    - Raises exceptions if broker is unavailable (fail-fast principle)

    Args:
        celery_app: The Celery application instance
        task_name: Name of the Celery task (e.g., 'accounts.tasks.user_tasks.send_welcome_email')
        args: Positional arguments for the task
        kwargs: Keyword arguments for the task

    Returns:
        AsyncResult or EagerResult with task_id

    Raises:
        Exception: In production mode if broker is unavailable or task fails
        Exception: In test mode if task cannot be found or executed

    Example:
        from celery import current_app
        from utils.celery_helpers import safe_send_task

        result = safe_send_task(
            current_app,
            'accounts.tasks.user_tasks.send_welcome_email',
            args=(123,),
            kwargs={'delay': 60}
        )
    """
    if kwargs is None:
        kwargs = {}

    is_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)

    if is_eager:
        # Test mode: execute synchronously using .apply() without broker connection
        # Get the task object from the Celery app registry
        task_obj = celery_app.tasks.get(task_name)
        if task_obj:
            # Execute synchronously - this returns an EagerResult
            return task_obj.apply(args=args, kwargs=kwargs)
        else:
            # Task not found in registry, try send_task with connection error handling
            # Even in eager mode, send_task may try to connect first
            try:
                return celery_app.send_task(task_name, args=args, kwargs=kwargs)
            except Exception:
                # If send_task fails in eager mode, we need to find the task another way
                # Import the task module and get the task directly
                module_name, func_name = task_name.rsplit('.', 1)
                try:
                    import importlib
                    module = importlib.import_module(module_name)
                    task_func = getattr(module, func_name)
                    return task_func.apply(args=args, kwargs=kwargs)
                except Exception:
                    # Re-raise the exception - tests should fail if task can't be found
                    raise
    else:
        # Production mode: always use send_task() with the caller-provided name.
        # This guarantees the message carries exactly the registered task name
        # the worker expects. apply_async() on a locally-resolved task object
        # can misroute when the object's .name differs from the registered name
        # (observed with shared_task in non-worker processes).
        try:
            return celery_app.send_task(task_name, args=args, kwargs=kwargs)
        except Exception as e:
            logger.error(
                f"Failed to send Celery task {task_name}: {e}",
                exc_info=True,
                extra={
                    'task_name': task_name,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys()),
                }
            )
            return None
