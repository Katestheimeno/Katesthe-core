"""
Sentry error-monitoring bootstrap.
Path: config/settings/monitoring.py

`sentry-sdk` is an OPTIONAL production dependency (see `pyproject.toml`
`[project.optional-dependencies].production`) — it is never installed at
runtime by default. `configure_sentry()` is safe to call unconditionally
from any settings module: it is a complete no-op (returns `False`) when
`SENTRY_DSN` is unset or when `sentry_sdk` is not importable, and it never
raises.
"""


def configure_sentry() -> bool:
    """Initialize Sentry if a DSN is configured and the SDK is installed.

    No-op (returns False) when SENTRY_DSN is empty or sentry_sdk is not
    installed. Safe to call from any settings module; never raises.
    """
    import os

    from config.settings.config import settings

    dsn = getattr(settings, "SENTRY_DSN", "") or ""
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError:
        return False

    release = getattr(getattr(settings, "project", None), "VERSION", None)
    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.1),
        environment=os.getenv("DJANGO_ENV", "production"),
        release=release,
        send_default_pii=False,
    )
    return True
