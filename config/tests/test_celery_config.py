"""
Tests for config/settings/celery.py — three-queue routing, beat schedule,
and the kombu-based queue declarations.

Reads `django.conf.settings` directly (already configured by pytest-django
with DJANGO_SETTINGS_MODULE=config.django.test); no DB access needed.
"""

from django.conf import settings


class TestCeleryQueues:
    def test_default_queue_is_default(self):
        assert settings.CELERY_TASK_DEFAULT_QUEUE == "default"

    def test_task_queues_declares_realtime_default_and_slow(self):
        assert {q.name for q in settings.CELERY_TASK_QUEUES} == {
            "realtime",
            "default",
            "slow",
        }

    def test_kombu_queue_import_succeeds(self):
        from kombu import Queue  # noqa: F401


class TestCeleryTaskRoutes:
    def test_flush_expired_jwt_tokens_routes_to_slow_queue(self):
        assert settings.CELERY_TASK_ROUTES["accounts.tasks.flush_expired_jwt_tokens"][
            "queue"
        ] == "slow"

    def test_process_permanent_deletions_is_not_a_live_route(self):
        assert "accounts.tasks.process_permanent_deletions" not in settings.CELERY_TASK_ROUTES


class TestCeleryBeatSchedule:
    def test_keep_warm_entry_present_with_expected_task_and_schedule(self):
        entry = settings.CELERY_BEAT_SCHEDULE["keep-warm"]

        assert entry["task"] == "utils.tasks.keep_warm"
        assert entry["schedule"] == 240.0

    def test_flush_expired_jwt_tokens_beat_entry_present(self):
        assert "flush-expired-jwt-tokens" in settings.CELERY_BEAT_SCHEDULE
