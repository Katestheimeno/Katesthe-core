"""
Manual pagination helper for non-ModelViewSet list endpoints.

Path: utils/pagination.py

Lists must be paginated (`.claude/rules/django.md` §2). This helper wraps a
queryset in the standard success envelope (`utils.api_response.ok`) and
embeds `meta.pagination` when a `?page` query param is present. `has_next`
is detected by over-fetching one extra row instead of running `.count()`.
"""

from __future__ import annotations

from utils.api_response import ok

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100


def paginate_or_ok(_viewset, queryset, serializer_class, request):
    """Serialize ``queryset`` and wrap it in the success envelope.

    Without a ``?page`` query param, returns the first ``_MAX_PAGE_SIZE``
    rows with no pagination metadata. With ``?page``, returns a page of
    ``page_size`` rows (default 20, max 100) plus a ``meta.pagination``
    block with ``page``, ``page_size``, ``has_next``, and ``has_previous``.

    ``_viewset`` is accepted for signature parity with callers that pass
    the viewset instance (e.g. for serializer context) but is unused here.
    """
    page_param = request.query_params.get("page")

    if page_param is None:
        rows = list(queryset[:_MAX_PAGE_SIZE])
        data = serializer_class(rows, many=True, context={"request": request}).data
        return ok(data, request)

    try:
        page = int(page_param)
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = int(request.query_params.get("page_size", _DEFAULT_PAGE_SIZE))
        page_size = max(1, min(page_size, _MAX_PAGE_SIZE))
    except (ValueError, TypeError):
        page_size = _DEFAULT_PAGE_SIZE

    offset = (page - 1) * page_size
    rows = list(queryset[offset : offset + page_size + 1])
    has_next = len(rows) > page_size
    rows = rows[:page_size]
    has_previous = page > 1

    data = serializer_class(rows, many=True, context={"request": request}).data

    return ok(
        data,
        request,
        meta_extra={
            "pagination": {
                "page": page,
                "page_size": page_size,
                "has_next": has_next,
                "has_previous": has_previous,
            }
        },
    )
