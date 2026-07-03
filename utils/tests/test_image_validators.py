"""
Tests for image upload validators (validate_image_size, validate_image_mime).
Path: utils/tests/test_image_validators.py
"""

from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from utils.validators import (
    MAX_IMAGE_UPLOAD_BYTES,
    validate_image_mime,
    validate_image_size,
)


class TestValidateImageSize:
    """Behavior of validate_image_size."""

    def test_no_raise_when_size_under_limit(self):
        file = SimpleNamespace(size=1024, content_type="image/png")

        validate_image_size(file)

    def test_no_raise_when_size_equal_to_limit(self):
        file = SimpleNamespace(size=MAX_IMAGE_UPLOAD_BYTES, content_type="image/png")

        validate_image_size(file)

    def test_raises_validation_error_when_size_exceeds_limit(self):
        file = SimpleNamespace(size=MAX_IMAGE_UPLOAD_BYTES + 1, content_type="image/png")

        with pytest.raises(ValidationError) as exc:
            validate_image_size(file)

        assert exc.value.code == "image_too_large"

    def test_silent_when_file_is_none(self):
        validate_image_size(None)

    def test_silent_when_size_is_none(self):
        file = SimpleNamespace(size=None, content_type="image/png")

        validate_image_size(file)

    def test_respects_custom_max_bytes(self):
        file = SimpleNamespace(size=101, content_type="image/png")

        with pytest.raises(ValidationError) as exc:
            validate_image_size(file, max_bytes=100)

        assert exc.value.code == "image_too_large"


class TestValidateImageMime:
    """Behavior of validate_image_mime."""

    def test_no_raise_when_mime_is_allowed(self):
        file = SimpleNamespace(size=1024, content_type="image/png")

        validate_image_mime(file)

    def test_raises_validation_error_when_mime_is_disallowed(self):
        file = SimpleNamespace(size=1024, content_type="application/pdf")

        with pytest.raises(ValidationError) as exc:
            validate_image_mime(file)

        assert exc.value.code == "image_invalid_type"

    def test_silent_when_file_is_none(self):
        validate_image_mime(None)

    def test_silent_when_content_type_is_none(self):
        file = SimpleNamespace(size=1024, content_type=None)

        validate_image_mime(file)

    def test_respects_custom_allowed_set(self):
        file = SimpleNamespace(size=1024, content_type="application/pdf")

        validate_image_mime(file, allowed=frozenset({"application/pdf"}))
