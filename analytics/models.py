from django.db import models


class AnalyticsDashboardPermission(models.Model):
    name = models.CharField(max_length=50, default='analytics', unique=True)

    class Meta:
        default_permissions = ()
        permissions = [
            ('view_analytics', 'Can view analytics dashboard'),
        ]

    def __str__(self) -> str:
        return self.name