"""
Tests for config/health.py — liveness and readiness endpoints.

The test URLConf (`config.urls_test`) does not include the health routes, so
readiness/liveness are exercised by calling the view functions directly with a
`RequestFactory` request.
"""
from unittest.mock import patch

import pytest
from django.test import RequestFactory, override_settings

from config import health


@pytest.fixture
def rf():
    return RequestFactory()


def test_liveness_returns_plaintext_ok(rf):
    request = rf.get("/health/")

    response = health.liveness(request)

    assert response.status_code == 200
    assert response.content == b"ok"
    assert response["Content-Type"] == "text/plain"


@pytest.mark.django_db
def test_readiness_returns_200_when_all_checks_pass(rf):
    request = rf.get("/ready/")

    with patch.object(health, "_check_redis", return_value=(True, "ok")):
        response = health.readiness(request)

    assert response.status_code == 200
    payload = _json(response)
    assert set(payload.keys()) == {"db", "redis", "celery"}
    assert payload["db"] == {"ok": True, "detail": "ok"}
    assert payload["redis"] == {"ok": True, "detail": "ok"}


@pytest.mark.django_db
def test_readiness_treats_eager_celery_as_ok(rf):
    request = rf.get("/ready/")

    with patch.object(health, "_check_redis", return_value=(True, "ok")):
        response = health.readiness(request)

    payload = _json(response)
    assert payload["celery"]["ok"] is True
    assert payload["celery"]["detail"] == "eager"


@pytest.mark.django_db
def test_readiness_returns_503_when_db_check_fails(rf):
    request = rf.get("/ready/")

    with (
        patch.object(health, "_check_db", return_value=(False, "down")),
        patch.object(health, "_check_redis", return_value=(True, "ok")),
    ):
        response = health.readiness(request)

    assert response.status_code == 503
    payload = _json(response)
    assert payload["db"] == {"ok": False, "detail": "down"}


def test_check_celery_returns_eager_without_pinging_broker():
    with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
        ok, detail = health._check_celery()

    assert ok is True
    assert detail == "eager"


def test_check_celery_pings_broker_when_not_eager():
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False):
        with patch("config.celery.app.control.ping", return_value=[{"worker": "ok"}]):
            ok, detail = health._check_celery()

    assert ok is True
    assert detail == "ok"


def test_check_celery_reports_no_workers_when_not_eager_and_no_replies():
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False):
        with patch("config.celery.app.control.ping", return_value=None):
            ok, detail = health._check_celery()

    assert ok is False
    assert detail == "fail:no_workers"


def test_check_celery_reports_failure_when_ping_raises():
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False):
        with patch("config.celery.app.control.ping", side_effect=ConnectionError("boom")):
            ok, detail = health._check_celery()

    assert ok is False
    assert detail == "fail:ConnectionError"


@pytest.mark.django_db
def test_check_db_returns_ok_against_real_test_database():
    ok, detail = health._check_db()

    assert ok is True
    assert detail == "ok"


def test_check_db_reports_failure_when_cursor_raises():
    with patch("config.health.connection") as mock_connection:
        mock_connection.cursor.side_effect = RuntimeError("boom")

        ok, detail = health._check_db()

    assert ok is False
    assert detail == "fail:RuntimeError"


def test_check_redis_returns_ok_when_ping_succeeds():
    with patch("config.health.redis.from_url") as mock_from_url:
        mock_client = mock_from_url.return_value
        mock_client.ping.return_value = True

        ok, detail = health._check_redis()

    assert ok is True
    assert detail == "ok"
    mock_client.close.assert_called_once()


def test_check_redis_reports_failure_when_ping_raises():
    with patch("config.health.redis.from_url") as mock_from_url:
        mock_client = mock_from_url.return_value
        mock_client.ping.side_effect = ConnectionError("unreachable")

        ok, detail = health._check_redis()

    assert ok is False
    assert detail == "fail:ConnectionError"


def _json(response):
    import json

    return json.loads(response.content)
