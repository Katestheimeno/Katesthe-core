"""Clear thread-local primary DB pin at HTTP request boundaries."""

from config.db_router import release_primary_for_request


class DBConsistencyMiddleware:
    """Prevent leaked primary-forcing flags across requests in the same worker."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        release_primary_for_request()
        try:
            return self.get_response(request)
        finally:
            release_primary_for_request()
