"""
Tests for the CopyableFieldMixin admin mixin.
Path: utils/tests/test_admin_mixins.py
"""

from pathlib import Path
from types import SimpleNamespace

from utils.admin.mixins import CopyableFieldMixin


class _DummyAdmin(CopyableFieldMixin):
    """Throwaway class mixing in CopyableFieldMixin for unit testing."""


class TestCopyableFieldMixin:
    """Test the CopyableFieldMixin methods (no DB required)."""

    def test_copyable_field_returns_span_with_data_code(self):
        result = _DummyAdmin().copyable_field("abc@x.com", "Email")

        assert 'data-code="abc@x.com"' in result
        assert 'class="copy-field"' in result

    def test_copyable_field_returns_default_display_when_falsy(self):
        result = _DummyAdmin().copyable_field("", "X")

        assert result == "-"

    def test_copyable_code_uses_code_copy_css_class(self):
        obj = SimpleNamespace(token="TKN123")

        result = _DummyAdmin().copyable_code(obj, "token")

        assert 'class="code-copy"' in result
        assert 'data-code="TKN123"' in result

    def test_copyable_email_reads_email_field(self):
        obj = SimpleNamespace(email="u@x.com")

        result = _DummyAdmin().copyable_email(obj)

        assert 'data-code="u@x.com"' in result


class TestCopyableFieldMixinMedia:
    """Test the inner Media class references static-relative asset paths."""

    def test_media_css_references_static_relative_path(self):
        css_paths = CopyableFieldMixin.Media.css["all"]

        assert css_paths == ("utils/admin/css/copy-field.css",)
        assert not css_paths[0].startswith("utils/static/")

    def test_media_js_references_static_relative_path(self):
        js_paths = CopyableFieldMixin.Media.js

        assert js_paths == ("utils/admin/js/copy-field.js",)
        assert not js_paths[0].startswith("utils/static/")


class TestCopyableFieldJsAsset:
    """Test the shipped JS asset ships no console.log debug statements."""

    def test_shipped_js_has_no_console_log(self):
        js_path = (
            Path(__file__).resolve().parent.parent
            / "static" / "utils" / "admin" / "js" / "copy-field.js"
        )

        contents = js_path.read_text()

        assert "console.log" not in contents
