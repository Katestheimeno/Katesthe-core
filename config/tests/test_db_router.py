"""
Tests for config/db_router.py and config/db_utils.py.
"""

from unittest.mock import patch

import pytest
from django.test import RequestFactory, override_settings

from config.db_router import (
    PrimaryReplicaRouter,
    _get_healthy_replica,
    force_primary_for_request,
    is_primary_forced,
    release_primary_for_request,
)
from config.db_utils import read_from_primary
from config.middleware.db_consistency import DBConsistencyMiddleware


class _DummyModel:
    pass


class TestPrimaryReplicaRouter:
    @pytest.fixture
    def router(self):
        return PrimaryReplicaRouter()

    @override_settings(
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
            "replica_0": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
        },
        REPLICA_DATABASE_ALIASES=["replica_0"],
        DB_ROUTING_ENABLED=True,
    )
    def test_db_for_read_uses_replica_when_healthy(self, router):
        with patch("config.db_router._get_healthy_replica", return_value="replica_0"):
            assert router.db_for_read(_DummyModel) == "replica_0"

    @override_settings(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        REPLICA_DATABASE_ALIASES=[],
        DB_ROUTING_ENABLED=False,
    )
    def test_db_for_read_primary_hint(self, router):
        assert router.db_for_read(_DummyModel, primary=True) == "default"

    @override_settings(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        REPLICA_DATABASE_ALIASES=[],
        DB_ROUTING_ENABLED=True,
    )
    def test_db_for_read_primary_when_routing_on_but_no_replicas(self, router):
        assert router.db_for_read(_DummyModel) == "default"

    @override_settings(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        REPLICA_DATABASE_ALIASES=["replica_0"],
        DB_ROUTING_ENABLED=True,
    )
    def test_db_for_read_forced_primary(self, router):
        force_primary_for_request()
        try:
            assert router.db_for_read(_DummyModel) == "default"
        finally:
            release_primary_for_request()

    def test_db_for_write_always_default(self, router):
        assert router.db_for_write(_DummyModel) == "default"

    def test_allow_migrate_only_default(self, router):
        assert router.allow_migrate("default", "auth") is True
        assert router.allow_migrate("replica_0", "auth") is False

    def test_allow_relation(self, router):
        assert router.allow_relation(None, None) is True


@override_settings(
    DATABASES={
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
        "replica_0": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
    },
    REPLICA_DATABASE_ALIASES=["replica_0"],
    DB_ROUTING_ENABLED=True,
)
def test_get_healthy_replica_returns_none_when_disabled():
    with override_settings(DB_ROUTING_ENABLED=False):
        assert _get_healthy_replica() is None


def test_read_from_primary_restores_flag():
    release_primary_for_request()
    assert is_primary_forced() is False
    with read_from_primary():
        assert is_primary_forced() is True
    assert is_primary_forced() is False


def test_read_from_primary_restores_after_exception():
    release_primary_for_request()

    with pytest.raises(RuntimeError):
        with read_from_primary():
            assert is_primary_forced() is True
            raise RuntimeError("boom")

    assert is_primary_forced() is False


def test_db_consistency_middleware_clears_flag():
    release_primary_for_request()
    factory = RequestFactory()
    request = factory.get("/")

    def get_response(_req):
        force_primary_for_request()
        from django.http import HttpResponse

        return HttpResponse("ok")

    mw = DBConsistencyMiddleware(get_response)
    mw(request)
    assert is_primary_forced() is False


def test_db_consistency_middleware_clears_on_exception():
    release_primary_for_request()

    def boom(_req):
        force_primary_for_request()
        raise ValueError("x")

    factory = RequestFactory()
    request = factory.get("/")
    mw = DBConsistencyMiddleware(boom)

    with pytest.raises(ValueError):
        mw(request)
    assert is_primary_forced() is False
