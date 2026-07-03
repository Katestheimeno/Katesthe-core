"""
Pytest configuration and fixtures for notifications app tests.
Path: notifications/tests/conftest.py

Minimal on purpose: the root `conftest.py` already exposes the shared
`user` / `api_client` fixtures project-wide (via `accounts/tests/conftest.py`).

Importing `config.celery` here ensures the project's configured Celery
`app` (with `task_always_eager=True` under `config.django.test`) is the
*current* Celery app before any `.delay()` call runs in these tests —
otherwise Celery falls back to an unconfigured default app and tries to
reach a real broker.
"""

import config.celery  # noqa: F401
