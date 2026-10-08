"""
Permission classes for GraphQL fields.

Nested fields (e.g. User.messages) don't need their own permission,
since they can only be reached through a root field that has one.
"""

import strawberry
from strawberry.permission import BasePermission


class IsAuthenticated(BasePermission):
    message = "Authentication required"

    def has_permission(self, source, info: strawberry.Info, **kwargs) -> bool:
        return info.context.is_authenticated


class IsAdmin(BasePermission):
    message = "Admin access required"

    def has_permission(self, source, info: strawberry.Info, **kwargs) -> bool:
        return info.context.is_admin
