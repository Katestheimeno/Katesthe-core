
# accounts/utils.py
from djoser import utils


def jwt_only_logout_user(request):
    """Skip token deletion if using JWT-only."""
    pass  # do nothing
