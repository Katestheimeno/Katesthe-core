"""
Tests for utils.models.make_upload_path.
Path: utils/tests/test_upload_paths.py
"""

import re

from utils.models import make_upload_path

try:
    from freezegun import freeze_time
    HAS_FREEZEGUN = True
except ImportError:
    HAS_FREEZEGUN = False


class TestMakeUploadPath:
    """Test the make_upload_path() factory."""

    def test_upload_path_matches_dated_pattern_and_lowercases_extension(self):
        """A regular filename produces a dated path with a lowercased extension."""
        upload_to = make_upload_path("avatars")
        result = upload_to(None, "photo.PNG")

        assert re.match(r"^avatars/\d{4}/\d{2}/\d{2}/photo_\d{6}\.png$", result)

    def test_upload_path_strips_path_traversal_components(self):
        """A filename with traversal components reduces to its basename."""
        upload_to = make_upload_path("docs")
        result = upload_to(None, "../../etc/passwd")

        assert re.match(r"^docs/\d{4}/\d{2}/\d{2}/passwd_\d{6}$", result)
        assert ".." not in result
        assert "/etc/" not in result

    def test_upload_path_uses_exact_frozen_date_when_freezegun_available(self):
        """When freezegun is installed, the date segment matches the frozen time exactly."""
        if not HAS_FREEZEGUN:
            import pytest
            pytest.skip("freezegun not installed")

        with freeze_time("2026-07-02 13:45:59"):
            upload_to = make_upload_path("avatars")
            result = upload_to(None, "photo.PNG")

        assert result == "avatars/2026/07/02/photo_134559.png"
