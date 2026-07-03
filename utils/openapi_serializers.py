"""Documentation-only serializers for drf-spectacular schema generation.
Path: utils/openapi_serializers.py

These serializers exist purely to shape the OpenAPI schema for the
`{"success", "data", "meta"}` response envelope (`.claude/rules/api.md`).
They carry no runtime behavior — nothing in the request/response cycle
instantiates or validates against them outside of schema generation.
"""

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers


@extend_schema_serializer(many=False)
class ApiEnvelopeJsonListSerializer(serializers.Serializer):
    """List-envelope shim.

    ``many=False`` stops drf-spectacular's list heuristic from wrapping the
    already-list-shaped ``data`` field in an extra outer array.
    """

    success = serializers.BooleanField()
    data = serializers.ListField(child=serializers.JSONField())
    meta = serializers.JSONField()
