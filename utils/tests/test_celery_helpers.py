"""
Tests for utils.celery_helpers safe Celery-dispatch helpers.
Path: utils/tests/test_celery_helpers.py
"""
from unittest.mock import Mock, patch

from django.test import override_settings

from utils.celery_helpers import (
    safe_send_task,
    safe_task_delay,
    safe_task_delay_with_countdown,
)


class TestSafeTaskDelayEager:
    """Eager mode (CELERY_TASK_ALWAYS_EAGER=True, the test-settings default)."""

    def test_safe_task_delay_calls_apply_with_args_and_kwargs(self):
        task = Mock()
        task.name = "some.task"

        result = safe_task_delay(task, 1, 2, foo="bar")

        task.apply.assert_called_once_with(args=(1, 2), kwargs={"foo": "bar"})
        task.delay.assert_not_called()
        assert result is task.apply.return_value

    def test_safe_task_delay_returns_none_when_apply_raises(self):
        task = Mock()
        task.name = "some.task"
        task.apply.side_effect = RuntimeError("broker unavailable")

        with patch("utils.celery_helpers.logger") as mock_logger:
            result = safe_task_delay(task, 1)

        assert result is None
        mock_logger.debug.assert_called_once()


class TestSafeTaskDelayProduction:
    """Production mode (CELERY_TASK_ALWAYS_EAGER=False)."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_safe_task_delay_calls_delay_with_args_and_kwargs(self):
        task = Mock()
        task.name = "some.task"

        result = safe_task_delay(task, 1, 2, foo="bar")

        task.delay.assert_called_once_with(1, 2, foo="bar")
        task.apply.assert_not_called()
        assert result is task.delay.return_value

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_safe_task_delay_returns_none_when_delay_raises(self):
        task = Mock()
        task.name = "some.task"
        task.delay.side_effect = RuntimeError("broker down")

        with patch("utils.celery_helpers.logger") as mock_logger:
            result = safe_task_delay(task, 1)

        assert result is None
        mock_logger.error.assert_called_once()


class TestSafeTaskDelayWithCountdownEager:
    """Eager mode ignores the countdown and behaves like safe_task_delay."""

    def test_safe_task_delay_with_countdown_calls_apply_in_eager_mode(self):
        task = Mock()
        task.name = "some.task"

        result = safe_task_delay_with_countdown(task, 30, 1, foo="bar")

        task.apply.assert_called_once_with(args=(1,), kwargs={"foo": "bar"})
        task.apply_async.assert_not_called()
        assert result is task.apply.return_value

    def test_safe_task_delay_with_countdown_returns_none_when_apply_raises(self):
        task = Mock()
        task.name = "some.task"
        task.apply.side_effect = RuntimeError("boom")

        with patch("utils.celery_helpers.logger") as mock_logger:
            result = safe_task_delay_with_countdown(task, 30)

        assert result is None
        mock_logger.debug.assert_called_once()


class TestSafeTaskDelayWithCountdownProduction:
    """Production mode schedules via apply_async with the given countdown."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_safe_task_delay_with_countdown_calls_apply_async_with_countdown(self):
        task = Mock()
        task.name = "some.task"

        result = safe_task_delay_with_countdown(task, 30, 1, foo="bar")

        task.apply_async.assert_called_once_with(
            args=(1,), kwargs={"foo": "bar"}, countdown=30
        )
        assert result is task.apply_async.return_value

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_safe_task_delay_with_countdown_returns_none_when_apply_async_raises(self):
        task = Mock()
        task.name = "some.task"
        task.apply_async.side_effect = RuntimeError("broker down")

        with patch("utils.celery_helpers.logger") as mock_logger:
            result = safe_task_delay_with_countdown(task, 30)

        assert result is None
        mock_logger.error.assert_called_once()


class TestSafeSendTaskEager:
    """Eager mode resolves the task by name before falling back."""

    def test_safe_send_task_uses_registry_hit(self):
        task_obj = Mock()
        celery_app = Mock()
        celery_app.tasks.get.return_value = task_obj

        result = safe_send_task(celery_app, "some.module.task", args=(1,), kwargs={"x": 1})

        celery_app.tasks.get.assert_called_once_with("some.module.task")
        task_obj.apply.assert_called_once_with(args=(1,), kwargs={"x": 1})
        assert result is task_obj.apply.return_value

    def test_safe_send_task_defaults_kwargs_to_empty_dict_when_none(self):
        task_obj = Mock()
        celery_app = Mock()
        celery_app.tasks.get.return_value = task_obj

        safe_send_task(celery_app, "some.module.task")

        task_obj.apply.assert_called_once_with(args=(), kwargs={})

    def test_safe_send_task_falls_back_to_send_task_when_not_in_registry(self):
        celery_app = Mock()
        celery_app.tasks.get.return_value = None

        result = safe_send_task(celery_app, "some.module.task", args=(1,))

        celery_app.send_task.assert_called_once_with("some.module.task", args=(1,), kwargs={})
        assert result is celery_app.send_task.return_value

    def test_safe_send_task_imports_module_directly_when_send_task_fails(self):
        celery_app = Mock()
        celery_app.tasks.get.return_value = None
        celery_app.send_task.side_effect = RuntimeError("broker unavailable")

        fake_module = Mock()
        fake_task_func = Mock()
        fake_module.task_func = fake_task_func

        with patch("importlib.import_module", return_value=fake_module) as mock_import:
            result = safe_send_task(
                celery_app, "some.module.task_func", args=(1,), kwargs={"x": 1}
            )

        mock_import.assert_called_once_with("some.module")
        fake_task_func.apply.assert_called_once_with(args=(1,), kwargs={"x": 1})
        assert result is fake_task_func.apply.return_value

    def test_safe_send_task_reraises_when_dynamic_import_also_fails(self):
        celery_app = Mock()
        celery_app.tasks.get.return_value = None
        celery_app.send_task.side_effect = RuntimeError("broker unavailable")

        with patch("importlib.import_module", side_effect=ImportError("no such module")):
            try:
                safe_send_task(celery_app, "some.module.task_func", args=(1,))
                assert False, "expected ImportError to propagate"
            except ImportError:
                pass


class TestSafeSendTaskProduction:
    """Production mode always dispatches through send_task by name."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_safe_send_task_calls_send_task_with_name(self):
        celery_app = Mock()

        result = safe_send_task(
            celery_app, "some.module.task", args=(1,), kwargs={"x": 1}
        )

        celery_app.send_task.assert_called_once_with(
            "some.module.task", args=(1,), kwargs={"x": 1}
        )
        assert result is celery_app.send_task.return_value

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_safe_send_task_returns_none_when_send_task_raises(self):
        celery_app = Mock()
        celery_app.send_task.side_effect = RuntimeError("broker down")

        with patch("utils.celery_helpers.logger") as mock_logger:
            result = safe_send_task(celery_app, "some.module.task", args=(1,))

        assert result is None
        mock_logger.error.assert_called_once()
