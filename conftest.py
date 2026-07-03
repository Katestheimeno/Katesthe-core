"""
Path: conftest.py
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.django.test")

import django
django.setup()

import importlib.util
import pathlib

import pytest
from django.core.cache import cache

# Expose the accounts test fixtures project-wide (config/tests, utils/tests, future apps).
#
# `accounts/tests/conftest.py` is also auto-discovered by pytest as a directory-scoped
# conftest, since it lives inside the `accounts/tests` testpath declared in pytest.ini.
# Simply listing it in `pytest_plugins` collides with that auto-discovery: pytest ends up
# trying to register the *same* imported module object under two different plugin names,
# which pluggy rejects ("Plugin already registered under a different name"). Loading it
# here from its file path, as an independent module object, under a name that does not
# end in "conftest.py", sidesteps that collision while still registering it as a *global*
# plugin (fixtures visible to every app's tests, not just `accounts/tests/`).
_ACCOUNTS_CONFTEST_PATH = pathlib.Path(__file__).parent / "accounts" / "tests" / "conftest.py"


def pytest_configure(config):
    """Register `accounts/tests/conftest.py`'s fixtures project-wide.

    See the module-level comment above for why this isn't a plain `pytest_plugins` entry.
    """
    pluginmanager = config.pluginmanager
    plugin_name = "accounts.tests.conftest"
    if pluginmanager.get_plugin(plugin_name) is not None:
        return

    spec = importlib.util.spec_from_file_location(plugin_name, _ACCOUNTS_CONFTEST_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pluginmanager.register(module, name=plugin_name)


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """Clear the Django cache before and after every test (prevents throttle-counter bleed)."""
    cache.clear()
    yield
    cache.clear()
