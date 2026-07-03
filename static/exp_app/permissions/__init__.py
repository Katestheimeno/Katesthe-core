"""
Permission classes for this app.

One `Is<Condition>` class per predicate; compose at the viewset:
    permission_classes = [IsAuthenticated, IsOwner]
`has_object_permission` gates the row (IDOR defense).
"""

# from rest_framework.permissions import BasePermission
#
#
# class IsOwner(BasePermission):
#     """Object-level permission: only the owner may access the object."""
#
#     def has_object_permission(self, request, view, obj):
#         return getattr(obj, "owner_id", None) == request.user.id
