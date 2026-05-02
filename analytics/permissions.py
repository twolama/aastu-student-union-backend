from rest_framework.permissions import BasePermission


class HasAnalyticsPermission(BasePermission):
    message = 'You do not have permission to view analytics.'

    def has_permission(self, request, view):  # type: ignore[override]
        return bool(request.user and request.user.is_authenticated and request.user.has_perm('analytics.view_analytics'))