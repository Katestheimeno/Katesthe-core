"""
Tests for utils.tasks.keep_warm.
Path: utils/tests/test_tasks.py
"""

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

import utils.tasks
from utils.tasks import keep_warm


@pytest.mark.django_db
class TestKeepWarmDbOnly:
    """No HEALTH_PING_URL configured — task only warms the DB connection."""

    def test_returns_none_and_never_calls_urlopen_when_ping_url_unset(self):
        with patch("utils.tasks.urllib.request.urlopen") as mock_urlopen:
            result = keep_warm()

        assert result is None
        mock_urlopen.assert_not_called()


@pytest.mark.django_db
class TestKeepWarmPingSuccess:
    """HEALTH_PING_URL configured — task GETs the health endpoint."""

    def test_calls_urlopen_with_health_endpoint_url_on_success(self):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_response

        with patch.object(utils.tasks, "_HEALTH_PING_URL", "http://x"), \
                patch("utils.tasks.urllib.request.urlopen", return_value=mock_cm) as mock_urlopen:
            keep_warm()

        mock_urlopen.assert_called_once()
        called_request = mock_urlopen.call_args[0][0]
        assert called_request.full_url == "http://x/api/v1/health/"


@pytest.mark.django_db
class TestKeepWarmPingHttpError:
    """An HTTPError from the health ping is logged as a warning, never raised."""

    def test_does_not_raise_on_http_error(self):
        http_error = urllib.error.HTTPError("http://x/api/v1/health/", 503, "err", {}, None)

        with patch.object(utils.tasks, "_HEALTH_PING_URL", "http://x"), \
                patch("utils.tasks.urllib.request.urlopen", side_effect=http_error):
            keep_warm()


@pytest.mark.django_db
class TestKeepWarmPingGenericError:
    """Any other exception from the health ping is logged as a warning, never raised."""

    def test_does_not_raise_on_generic_exception(self):
        with patch.object(utils.tasks, "_HEALTH_PING_URL", "http://x"), \
                patch("utils.tasks.urllib.request.urlopen", side_effect=Exception("boom")):
            keep_warm()
