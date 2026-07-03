# Standalone `django-notification-system` — Extraction Plan

**Source:** `/home/tmpusr/Documents/github/Rhitoric-core/notification_system/`
**Target:** A `pip install`-able Django package
**Estimated effort:** 2-3 focused days
**Prerequisites:** None — the app's adapter pattern already supports pluggable overrides

---

## Overview

The Rhitoric `notification_system` app is already 80% standalone. It uses
`settings.AUTH_USER_MODEL` for all user FKs, `import_string()` for pluggable
adapters, and `getattr(settings, ..., default)` for all configuration. The
remaining 20% is 10 project-internal imports that need to be inlined, abstracted,
or made optional.

### What the package provides

- **Type/category registry** — projects register notification types at startup via `AppConfig.ready()`
- **Dispatch engine** — deduplication, preference checks, two-channel delivery (WebSocket + email)
- **Two-level user preferences** — per-category enable/disable + per-type in_app/email
- **Delivery logging** — `NotificationDeliveryLog` with channel, status, timestamps
- **8 REST API endpoints** — list, detail, unread count, mark read, mark all read, delete, preferences list, preferences update
- **WebSocket consumer** — real-time delivery via Django Channels
- **Management command** — `bootstrap_notification_preferences` with `--dry-run` and `--batch-size`
- **Admin interface** — 4 model admins with search, filters, display columns

---

## 1. Package structure

```
django-notification-system/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── notification_system/
│   ├── __init__.py              # __version__, default_app_config
│   ├── apps.py                  # AppConfig — calls register function in ready()
│   ├── conf.py                  # NEW — centralized settings with defaults
│   ├── constants.py             # Priority, Channel, DeliveryStatus (no changes)
│   ├── registry.py              # NotificationTypeRegistry (strip Rhitoric types)
│   ├── adapters.py              # Generic defaults (strip elearning/clubs)
│   ├── errors.py                # NEW — error code constants (inlined from errors/catalog.py)
│   ├── logging.py               # NEW — stdlib logger wrapper (replaces config.logger)
│   ├── utils.py                 # WebSocket send utility (swap logger)
│   ├── compat.py                # NEW — optional-dependency helpers
│   ├── consumers.py             # WebSocket consumer (strip game handlers, abstract auth)
│   ├── pagination.py            # NEW — inlined parse_page_params
│   ├── throttling.py            # NEW — inlined throttle classes
│   ├── models/
│   │   ├── __init__.py
│   │   ├── _notification.py
│   │   ├── _category_preference.py
│   │   ├── _notification_preference.py
│   │   └── _delivery_log.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── _dispatch.py
│   │   ├── _actions.py
│   │   ├── _preferences.py
│   │   ├── _broadcast.py
│   │   └── _registry.py         # backward-compat re-export shim
│   ├── selectors/
│   │   ├── __init__.py
│   │   ├── _notification.py
│   │   ├── _preference.py
│   │   └── _user_roles.py
│   ├── serializers/
│   │   ├── __init__.py
│   │   ├── _notification.py
│   │   ├── _preference.py
│   │   └── _category_preference.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── _list.py
│   │   ├── _actions.py
│   │   └── _preferences.py
│   ├── urls/
│   │   └── __init__.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── _email.py
│   ├── admin/
│   │   └── __init__.py
│   ├── management/
│   │   └── commands/
│   │       └── bootstrap_notification_preferences.py
│   ├── migrations/
│   │   ├── __init__.py
│   │   └── 0001_initial.py
│   └── tests/                   # ships with the package
│       ├── __init__.py
│       ├── conftest.py
│       ├── factories.py
│       ├── test_settings.py     # NEW — minimal Django settings for standalone tests
│       ├── models/
│       ├── services/
│       ├── controllers/
│       ├── selectors/
│       ├── consumers/
│       └── management/
└── tests/                       # integration test project (optional)
    ├── manage.py
    └── settings.py
```

---

## 2. New files to create

### 2.1 `conf.py` — centralized settings

Single place that reads all `NOTIFICATION_*` settings with defaults. Every other
module imports from here instead of scattered `getattr(settings, ...)` calls.

```python
from django.conf import settings

class NotificationSettings:
    """Lazy settings accessor with documented defaults."""

    @property
    def RETENTION_DAYS(self):
        return getattr(settings, "NOTIFICATION_RETENTION_DAYS", 90)

    @property
    def DEDUPE_WINDOW_MINUTES(self):
        return getattr(settings, "NOTIFICATION_DEDUPE_WINDOW_MINUTES", 5)

    @property
    def SHOULD_SKIP_FOR_USER(self):
        """Dotted path to a callable(user_id, notification_type) -> bool.
        If None, no skip logic is applied."""
        return getattr(settings, "NOTIFICATION_SHOULD_SKIP_FOR_USER", None)

    @property
    def GET_USER_ROLES(self):
        """Dotted path to a callable(user) -> list[str].
        Default returns Django group names."""
        return getattr(
            settings,
            "NOTIFICATION_GET_USER_ROLES",
            "notification_system.adapters.get_user_roles",
        )

    @property
    def THROTTLE_ENABLED(self):
        return getattr(settings, "THROTTLE_ENABLED", True)

    @property
    def WS_AUTH_MIDDLEWARE(self):
        """Dotted path to an async callable(scope) -> User|AnonymousUser.
        If None, uses Django Channels' built-in AuthMiddlewareStack."""
        return getattr(settings, "NOTIFICATION_WS_AUTH_MIDDLEWARE", None)

    @property
    def DEFAULT_FROM_EMAIL(self):
        return getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")

notification_settings = NotificationSettings()
```

### 2.2 `errors.py` — error code constants

Inlined from `errors/catalog.py`. The package ships its own error codes.

```python
NOTIFICATION__NOT_FOUND = "NOTIFICATION__NOT_FOUND"
NOTIFICATION__DELIVERY_LOG_NOT_FOUND = "NOTIFICATION__DELIVERY_LOG_NOT_FOUND"
NOTIFICATION__DELIVERY_NOT_RETRYABLE = "NOTIFICATION__DELIVERY_NOT_RETRYABLE"
NOTIFICATION__PREFERENCE_NOT_FOUND = "NOTIFICATION__PREFERENCE_NOT_FOUND"
NOTIFICATION__CATEGORY_PREFERENCE_NOT_FOUND = "NOTIFICATION__CATEGORY_PREFERENCE_NOT_FOUND"
NOTIFICATION__NO_RECIPIENTS = "NOTIFICATION__NO_RECIPIENTS"
```

### 2.3 `logging.py` — stdlib logger

Replaces all `from config.logger import logger` imports. Uses stdlib `logging`
so the package works with any logging setup (structlog, loguru, vanilla).

```python
import logging

logger = logging.getLogger("notification_system")
```

All 5 files that import `config.logger` change to:
```python
from notification_system.logging import logger
```

### 2.4 `pagination.py` — inlined from `utils/pagination.py`

```python
from typing import Tuple

def parse_page_params(request, *, page_default=1, page_size_default=20, page_size_max=100) -> Tuple[int, int]:
    try:
        page = max(1, int(request.GET.get("page") or page_default))
    except (TypeError, ValueError):
        page = page_default
    try:
        page_size = int(request.GET.get("page_size") or page_size_default)
        page_size = max(1, min(page_size_max, page_size))
    except (TypeError, ValueError):
        page_size = page_size_default
    return page, page_size
```

### 2.5 `throttling.py` — inlined from `utils/throttling.py`

```python
from rest_framework.throttling import SimpleRateThrottle
from notification_system.conf import notification_settings


class _UserOrIPThrottle(SimpleRateThrottle):
    def allow_request(self, request, view):
        if not notification_settings.THROTTLE_ENABLED:
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class NotificationActionThrottle(_UserOrIPThrottle):
    scope = "notification_action"


class NotificationBulkThrottle(_UserOrIPThrottle):
    scope = "notification_bulk"
```

Projects configure rates in `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`:
```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "notification_action": "60/min",
        "notification_bulk": "10/min",
    }
}
```

### 2.6 `compat.py` — optional dependency helpers

```python
import contextlib

def safe_task_delay(task, *args, **kwargs):
    """Dispatch a Celery task, swallowing broker errors."""
    from django.conf import settings
    is_eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    if is_eager:
        try:
            return task.apply(args=args, kwargs=kwargs)
        except Exception:
            return None
    try:
        return task.delay(*args, **kwargs)
    except Exception:
        from notification_system.logging import logger
        logger.exception("Failed to queue task %s", task.name)
        return None


@contextlib.contextmanager
def read_from_primary():
    """No-op context manager. Projects with primary/replica routing
    should override NOTIFICATION_READ_FROM_PRIMARY_CONTEXT in settings
    or monkey-patch this."""
    try:
        from django.conf import settings
        path = getattr(settings, "NOTIFICATION_READ_FROM_PRIMARY_CONTEXT", None)
        if path:
            from django.utils.module_loading import import_string
            cm = import_string(path)
            with cm():
                yield
            return
    except Exception:
        pass
    yield
```

---

## 3. Dependency cuts — file-by-file changes

### 3.1 `consumers.py` — heaviest rewrite

**Current project imports to remove:**
```python
from config.logger import logger                                    # → notification_system.logging
from utils.middleware.jwt_websocket_auth import (
    get_accepted_subprotocol, jwt_auth_failed,                      # → inline or pluggable
)
from utils.websocket.rate_limit import MessageRateLimiter           # → inline
from utils.websocket.protocol import handle_auth_rotate             # → inline
```

**What to inline:**

1. **`MessageRateLimiter`** — 20-line class, zero dependencies beyond stdlib.
   Copy verbatim into `consumers.py` or a new `notification_system/ws_utils.py`.

   ```python
   from collections import deque
   from time import monotonic

   class MessageRateLimiter:
       __slots__ = ("_max_messages", "_window_seconds", "_timestamps")
       def __init__(self, max_messages=15, window_seconds=1.0):
           self._max_messages = max_messages
           self._window_seconds = window_seconds
           self._timestamps = deque(maxlen=max_messages)
       def is_throttled(self):
           now = monotonic()
           while self._timestamps and now - self._timestamps[0] > self._window_seconds:
               self._timestamps.popleft()
           if len(self._timestamps) >= self._max_messages:
               return True
           self._timestamps.append(now)
           return False
   ```

2. **`get_accepted_subprotocol`** — 5-line pure function, no imports.
   ```python
   def get_accepted_subprotocol(scope):
       if scope.get("_auth_via_subprotocol"):
           return "access_token"
       if "access_token" in scope.get("subprotocols", []):
           return "access_token"
       return None
   ```

3. **`jwt_auth_failed`** — 1-line pure function, no imports.
   ```python
   def jwt_auth_failed(scope):
       return bool(scope.get("jwt_auth_failed"))
   ```

4. **`handle_auth_rotate`** — depends on `get_user_from_token`, which is a
   project-specific JWT validator. Make this **pluggable via settings**:

   ```python
   async def handle_auth_rotate(consumer, data):
       token = data.get("token")
       if not token:
           await consumer.send_json({"type": "auth_rotate_failed", "code": "AUTH__TOKEN_MISSING"})
           return

       get_user = _resolve_auth_rotate_handler()
       if get_user is None:
           await consumer.send_json({"type": "auth_rotate_failed", "code": "AUTH__NOT_CONFIGURED"})
           return

       user = await get_user(token)
       if user is None or user.is_anonymous:
           await consumer.send_json({"type": "auth_rotate_failed", "code": "AUTH__TOKEN_INVALID"})
           return

       consumer.scope["user"] = user
       consumer.user = user
       await consumer.send_json({"type": "auth_rotated", "user_id": str(user.pk)})


   def _resolve_auth_rotate_handler():
       from notification_system.conf import notification_settings
       path = notification_settings.WS_AUTH_MIDDLEWARE
       if not path:
           return None
       from django.utils.module_loading import import_string
       return import_string(path)
   ```

5. **Strip domain-specific no-op handlers.** Remove these methods entirely:
   - `player_joined`
   - `player_left_game`
   - `game_abandoned`
   - `game_completed`
   - `vote_cast`

### 3.2 `utils.py`

```python
# BEFORE
from config.logger import logger

# AFTER
from notification_system.logging import logger
```

No other changes needed. `asgiref` and `channels` are already declared
third-party deps.

### 3.3 `services/_dispatch.py`

Three changes:

```python
# 1. Logger
# BEFORE: from config.logger import logger
# AFTER:
from notification_system.logging import logger

# 2. safe_task_delay
# BEFORE: from utils.celery_helpers import safe_task_delay
# AFTER:
from notification_system.compat import safe_task_delay

# 3. Settings access — use conf.py
# BEFORE: getattr(settings, "NOTIFICATION_RETENTION_DAYS", 90)
# AFTER:
from notification_system.conf import notification_settings
# then: notification_settings.RETENTION_DAYS
```

### 3.4 `services/_broadcast.py`

```python
# BEFORE: from config.logger import logger
# AFTER:
from notification_system.logging import logger
```

### 3.5 `tasks/_email.py`

Three changes:

```python
# 1. Logger
# BEFORE: from config.logger import logger
# AFTER:
from notification_system.logging import logger

# 2. read_from_primary
# BEFORE: from config.db_utils import read_from_primary
# AFTER:
from notification_system.compat import read_from_primary

# 3. from_email fallback
# BEFORE: from_email = from_email or getattr(django_settings, "EMAIL_HOST_USER", None) or "noreply@rhitoric.com"
# AFTER:
from notification_system.conf import notification_settings
# then: from_email = from_email or notification_settings.DEFAULT_FROM_EMAIL
```

### 3.6 `controllers/_list.py`

```python
# BEFORE
from errors.catalog import NOTIFICATION__NOT_FOUND
from utils.pagination import parse_page_params
from utils.throttling import NotificationActionThrottle

# AFTER
from notification_system.errors import NOTIFICATION__NOT_FOUND
from notification_system.pagination import parse_page_params
from notification_system.throttling import NotificationActionThrottle
```

### 3.7 `controllers/_actions.py`

```python
# BEFORE
from errors.catalog import NOTIFICATION__NOT_FOUND
from utils.throttling import NotificationActionThrottle, NotificationBulkThrottle

# AFTER
from notification_system.errors import NOTIFICATION__NOT_FOUND
from notification_system.throttling import NotificationActionThrottle, NotificationBulkThrottle
```

### 3.8 `controllers/_preferences.py`

```python
# BEFORE
from utils.throttling import NotificationActionThrottle

# AFTER
from notification_system.throttling import NotificationActionThrottle
```

### 3.9 `admin/__init__.py`

```python
# BEFORE
from unfold.admin import ModelAdmin

# AFTER — conditional import
try:
    from unfold.admin import ModelAdmin
except ImportError:
    from django.contrib.admin import ModelAdmin
```

### 3.10 `adapters.py` — strip domain logic

Replace the entire file with generic defaults:

```python
from django.contrib.auth import get_user_model

User = get_user_model()


def should_skip_notification_for_user(user_id, notification_type):
    """Default: never skip. Override via NOTIFICATION_SHOULD_SKIP_FOR_USER setting."""
    return False


def get_user_roles(user):
    """Default: return Django group names. Override via NOTIFICATION_GET_USER_ROLES setting."""
    if hasattr(user, "groups"):
        return list(user.groups.values_list("name", flat=True))
    return []
```

### 3.11 `registry.py` — strip Rhitoric types

Keep the `NotificationTypeConfig` dataclass, `NotificationTypeRegistry` class,
and `CATEGORIES` dict. Replace contents:

```python
CATEGORIES = {}  # empty — projects populate in their AppConfig.ready()

def register_core_types():
    """No-op in the base package. Projects register their own types."""
    pass
```

Document the registration pattern for users:

```python
# myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    def ready(self):
        from notification_system.registry import NotificationTypeRegistry, CATEGORIES

        CATEGORIES.update({
            "orders": "Orders",
            "support": "Support",
        })

        NotificationTypeRegistry.register(
            "orders.placed",
            priority="normal",
            default_in_app=True,
            default_email=True,
        )
```

### 3.12 `apps.py` — conditional registration

```python
from django.apps import AppConfig

class NotificationSystemConfig(AppConfig):
    name = "notification_system"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Projects can set NOTIFICATION_AUTO_REGISTER_TYPES = False
        # to skip the (now empty) register_core_types and handle it themselves.
        from django.conf import settings
        if getattr(settings, "NOTIFICATION_AUTO_REGISTER_TYPES", True):
            from notification_system.registry import register_core_types
            register_core_types()
```

---

## 4. Third-party dependency strategy

### Required (hard dependencies)

| Package | Why | Min version |
|---------|-----|-------------|
| `django` | ORM, auth, settings, mail, management commands | >=4.2 |
| `djangorestframework` | API views, serializers, permissions | >=3.14 |
| `drf-spectacular` | OpenAPI schema decorators on controllers | >=0.27 |
| `django-model-utils` | `TimeStampedModel` base class for `Notification` | >=4.3 |

### Optional (extras)

| Package | Extra name | Why | What breaks without it |
|---------|-----------|-----|----------------------|
| `channels` | `[ws]` | WebSocket consumer + channel layer send | No real-time delivery; `utils.send_notification_to_user` returns `False` |
| `asgiref` | `[ws]` | `async_to_sync` bridge for channel layer | Same as above |
| `celery` | `[celery]` | Async email delivery task | Email task unavailable; dispatch logs warning |
| `django-unfold` | `[unfold]` | Themed admin interface | Falls back to stock `django.contrib.admin.ModelAdmin` |

### `pyproject.toml` dependency section

```toml
[project]
name = "django-notification-system"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "django>=4.2",
    "djangorestframework>=3.14",
    "drf-spectacular>=0.27",
    "django-model-utils>=4.3",
]

[project.optional-dependencies]
ws = ["channels>=4.0", "asgiref>=3.7"]
celery = ["celery>=5.3"]
unfold = ["django-unfold>=0.40"]
all = ["django-notification-system[ws,celery,unfold]"]
dev = [
    "django-notification-system[all]",
    "pytest>=7.0",
    "pytest-django>=4.5",
    "pytest-asyncio>=0.21",
    "factory-boy>=3.3",
]
```

### Guarding optional imports

In `compat.py` or at the top of files that use optional deps:

```python
# utils.py — channels is optional
try:
    from channels.layers import get_channel_layer
    HAS_CHANNELS = True
except ImportError:
    HAS_CHANNELS = False

def send_notification_to_user(user_id, event_type, data):
    if not HAS_CHANNELS:
        logger.debug("channels not installed — skipping WS delivery")
        return False
    # ... existing logic
```

```python
# tasks/_email.py — celery is optional
try:
    from celery import shared_task
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False
    def shared_task(**kwargs):
        """No-op decorator when celery is not installed."""
        def wrapper(fn):
            fn.delay = lambda *a, **kw: None
            fn.apply = lambda *a, **kw: None
            return fn
        return wrapper
```

---

## 5. Settings reference (for package README)

All settings are optional. Defaults shown.

```python
# ── Core ──
NOTIFICATION_RETENTION_DAYS = 90             # days before notifications are excluded from queries
NOTIFICATION_DEDUPE_WINDOW_MINUTES = 5       # deduplication window for same dedupe_key
NOTIFICATION_AUTO_REGISTER_TYPES = True      # call register_core_types() in AppConfig.ready()

# ── Adapters (dotted paths to callables) ──
NOTIFICATION_SHOULD_SKIP_FOR_USER = None     # callable(user_id: int, notification_type: str) -> bool
NOTIFICATION_GET_USER_ROLES = "notification_system.adapters.get_user_roles"  # callable(user) -> list[str]

# ── WebSocket ──
NOTIFICATION_WS_AUTH_MIDDLEWARE = None        # async callable(token: str) -> User|None (for auth_rotate)

# ── Email ──
# Uses Django's DEFAULT_FROM_EMAIL for the sender address.
# Uses Django's EMAIL_BACKEND for delivery.

# ── Primary/replica DB routing ──
NOTIFICATION_READ_FROM_PRIMARY_CONTEXT = None  # dotted path to a context manager

# ── Throttling ──
THROTTLE_ENABLED = True                      # global kill-switch for throttle classes
# Rates configured in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]:
#   "notification_action": "60/min"
#   "notification_bulk": "10/min"
```

---

## 6. Installation instructions (for package README)

```bash
pip install django-notification-system
# With WebSocket support:
pip install django-notification-system[ws]
# With Celery email delivery:
pip install django-notification-system[celery]
# Everything:
pip install django-notification-system[all]
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "drf_spectacular",
    "notification_system",
]

# urls.py
urlpatterns = [
    path("api/v1/", include(("notification_system.urls", "notification_system"))),
]

# (optional) routing.py — for WebSocket
from notification_system.consumers import NotificationConsumer
websocket_urlpatterns = [
    re_path(r"^ws/notifications/$", NotificationConsumer.as_asgi()),
]
```

```bash
python manage.py migrate notification_system
python manage.py bootstrap_notification_preferences --dry-run
```

---

## 7. Migration handling

The package ships its own `migrations/` directory. When users install it:

1. `python manage.py migrate notification_system` creates all 4 tables
2. All FKs use `settings.AUTH_USER_MODEL` — works with any custom user model
3. The `0001_initial.py` migration declares `swappable_dependency(settings.AUTH_USER_MODEL)`

**For existing Rhitoric/Katesthe-core projects** that already have
`notification_system` tables: the migration history is compatible as long as the
migration filenames and operations match. If the standalone package resets
migrations, provide a `--fake-initial` instruction.

---

## 8. Test strategy

### Standalone test runner

Ship a minimal `tests/test_settings.py`:

```python
SECRET_KEY = "test-secret-key"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.admin",
    "rest_framework",
    "drf_spectacular",
    "notification_system",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
ROOT_URLCONF = "notification_system.urls"
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "notification_action": "60/min",
        "notification_bulk": "10/min",
    }
}
AUTH_USER_MODEL = "auth.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

### Test changes

All test files that import project utilities need the same import swaps:

| Before | After |
|--------|-------|
| `from game.tests.factories import UserFactory` | Use a `UserFactory` shipped with the package tests |
| `from accounts.tests.factories import UserFactory` | Same |
| `from utils.throttling import ...` | `from notification_system.throttling import ...` |
| `from accounts.tasks.bootstrap_tasks import bootstrap_new_user` | Remove or mock — test the management command directly |

Ship a `tests/factories.py` with the package:

```python
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
```

### Run tests

```bash
cd django-notification-system/
pip install -e ".[dev]"
pytest --ds=notification_system.tests.test_settings
```

---

## 9. Execution checklist

### Day 1 — Cut dependencies

- [ ] Create package directory structure
- [ ] Create `conf.py` with all settings
- [ ] Create `errors.py` with error constants
- [ ] Create `logging.py` with stdlib logger
- [ ] Create `pagination.py` (inline `parse_page_params`)
- [ ] Create `throttling.py` (inline throttle classes)
- [ ] Create `compat.py` (`safe_task_delay`, `read_from_primary`)
- [ ] Rewrite `adapters.py` (generic defaults)
- [ ] Rewrite `registry.py` (strip Rhitoric types, empty `CATEGORIES`)
- [ ] Rewrite `consumers.py` (inline rate limiter, WS auth helpers; strip game handlers; pluggable auth_rotate)
- [ ] Update all 5 `config.logger` imports → `notification_system.logging`
- [ ] Update all `errors.catalog` imports → `notification_system.errors`
- [ ] Update all `utils.pagination` imports → `notification_system.pagination`
- [ ] Update all `utils.throttling` imports → `notification_system.throttling`
- [ ] Update `utils.celery_helpers` import → `notification_system.compat`
- [ ] Update `config.db_utils` import → `notification_system.compat`
- [ ] Update `admin/__init__.py` with conditional unfold import
- [ ] Update `tasks/_email.py` from_email fallback → `notification_settings.DEFAULT_FROM_EMAIL`
- [ ] Guard channels imports with `try/except ImportError`
- [ ] Guard celery imports with `try/except ImportError`
- [ ] Verify: `grep -r "from config\." notification_system/` returns zero hits
- [ ] Verify: `grep -r "from utils\." notification_system/` returns zero hits
- [ ] Verify: `grep -r "from errors\." notification_system/` returns zero hits
- [ ] Verify: `grep -rn "rhitoric\|elearning\|ClubMembership\|game\.\|accounts\." notification_system/` returns zero production code hits

### Day 2 — Package & test

- [ ] Create `pyproject.toml` with dependencies and extras
- [ ] Create `README.md` with installation, settings reference, usage examples
- [ ] Create `tests/test_settings.py` (minimal Django config)
- [ ] Ship `tests/factories.py` with generic `UserFactory`
- [ ] Update all test imports to use package-internal paths
- [ ] Remove test references to `accounts`, `game`, `elearning` apps
- [ ] Run: `pytest --ds=notification_system.tests.test_settings` — all green
- [ ] Run: `python -c "import notification_system"` — no import errors
- [ ] Test without channels: `pip uninstall channels && pytest` — WS tests skip, rest pass
- [ ] Test without celery: `pip uninstall celery && pytest` — email tests skip, rest pass

### Day 3 — Polish

- [ ] Write `CHANGELOG.md`
- [ ] Add `LICENSE` file
- [ ] Add type hints to all public API functions in `__init__.py` re-exports
- [ ] Verify migrations work on a fresh SQLite DB
- [ ] Verify migrations work with a custom user model (`AUTH_USER_MODEL = "myapp.User"`)
- [ ] Build: `python -m build`
- [ ] Test install from wheel: `pip install dist/django_notification_system-0.1.0-py3-none-any.whl`
- [ ] Document the registration pattern with a "Quick Start" example in README
- [ ] Document the adapter override pattern with a "Customization" section
- [ ] Tag v0.1.0

---

## 10. Remaining design decisions

These are decisions to make during execution, not blockers:

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Package name on PyPI | `django-notification-system`, `django-notifications-engine`, `dj-notifications` | `django-notification-system` — matches the app label |
| `model_utils.TimeStampedModel` dependency | Keep it (adds `created`/`modified`) vs. inline the two fields | Keep — it's a well-maintained 1-dependency lib |
| `drf-spectacular` as hard dep | Hard (current) vs. optional with conditional `@extend_schema` | Hard — the package ships API views, schema should be documented |
| Ship admin or make optional | Always register admin vs. `NOTIFICATION_ADMIN_ENABLED` setting | Always register — it's 40 lines, zero cost if unused |
| WebSocket consumer auth | Pluggable via settings (current plan) vs. ship a default JWT auth | Pluggable — JWT implementation varies wildly across projects |
| Minimum Django version | 4.2 LTS vs. 5.0+ | 4.2 — no features require 5.x, wider compatibility |
| Test DB backend | SQLite (fast, portable) vs. PostgreSQL (matches production) | SQLite for package CI; projects test against their own DB |

---

## 11. What NOT to do

1. **Don't copy Rhitoric's 38 notification types** into the base package — they are domain-specific
2. **Don't ship the `backends/tickets.py`** file — it's a Rhitoric integration
3. **Don't hardcode `noreply@rhitoric.com`** anywhere — use `settings.DEFAULT_FROM_EMAIL`
4. **Don't depend on `loguru`** — use stdlib `logging` so any logger works
5. **Don't make channels/celery hard dependencies** — the package must work for HTTP-only + synchronous setups
6. **Don't inline the full JWT auth middleware** — it's too project-specific; keep it pluggable
7. **Don't reset migrations** if you plan to upgrade existing Rhitoric/Katesthe installs — maintain compatibility
