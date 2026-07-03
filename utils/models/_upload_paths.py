"""
Factory for dated, path-traversal-safe file upload paths.
Path: utils/models/_upload_paths.py
"""

import os

from django.utils import timezone

__all__ = ["make_upload_path"]


def make_upload_path(subdir: str):
    """Return an `upload_to` callable -> '<subdir>/YYYY/MM/DD/<name>_HHMMSS.<ext>'."""
    def _upload_to(instance, filename: str) -> str:
        base = os.path.basename(filename)          # strip client path components / traversal
        name, ext = os.path.splitext(base)
        now = timezone.now()
        stamped = f"{name}_{now:%H%M%S}{ext.lower()}"
        return f"{subdir}/{now:%Y}/{now:%m}/{now:%d}/{stamped}"
    return _upload_to
