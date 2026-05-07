from rest_framework.permissions import BasePermission


class HasAnalyticsPermission(BasePermission):
    message = 'You do not have permission to view analytics.'

    def has_permission(self, request, view):  # type: ignore[override]
        if not (request.user and request.user.is_authenticated):
            return False
            
        # Staff and superusers always have access
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Check for explicit permission
        if request.user.has_perm('analytics.view_analytics'):
            return True
            
        # Allow authenticated users to view the dashboard itself
        # (The view will handle internal data filtering if needed)
        if view.__class__.__name__ == 'AnalyticsDashboardView':
            return True
            
        return False