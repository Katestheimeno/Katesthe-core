"""
Custom authentication backends for this app.

Uncomment and adapt when you need app-specific auth. Wire into a view via
`authentication_classes = [ExampleTokenAuthentication]` or globally in
`config/settings/restframework.py` DEFAULT_AUTHENTICATION_CLASSES.
"""

# from rest_framework.authentication import BaseAuthentication
# from rest_framework.exceptions import AuthenticationFailed
#
#
# class ExampleTokenAuthentication(BaseAuthentication):
#     """Authenticate via a custom header. Return (user, auth) or None."""
#
#     def authenticate(self, request):
#         token = request.headers.get("X-Example-Token")
#         if not token:
#             return None
#         # ... resolve the user from the token ...
#         # raise AuthenticationFailed("Invalid token") on failure
#         return None
