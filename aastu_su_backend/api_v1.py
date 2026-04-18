from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from users.views import UserViewSet, RoleViewSet, ForgotPasswordView, ResetPasswordView, CustomTokenObtainPairView
from announcements.views import AnnouncementViewSet, AnnouncementCategoryViewSet
from core.views import (
    SystemStatsView,
    HealthCheckView,
    CollegeViewSet,
    DepartmentViewSet,
    AnalyticsDashboardView,
    AnalyticsReportExportView,
)
from bookings.views import BookingViewSet
from clubs.views import ClubViewSet, ClubCategoryViewSet
from events.views import EventViewSet, EventVolunteerViewSet
from users.views import UserViewSet
from venues.views import VenueViewSet, VenueImageViewSet, VenueCategoryViewSet

router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet)
router.register(r'announcement-categories', AnnouncementCategoryViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'clubs', ClubViewSet)
router.register(r'club-categories', ClubCategoryViewSet)
router.register(r'events', EventViewSet)
router.register(r'volunteers', EventVolunteerViewSet, basename='volunteer')
router.register(r'users', UserViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'colleges', CollegeViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'venues', VenueViewSet)
router.register(r'venue-categories', VenueCategoryViewSet)
router.register(r'venue-gallery', VenueImageViewSet)

urlpatterns = [
    # Auth endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    
    # System Health
    path('system/stats/', SystemStatsView.as_view(), name='system_stats'),
    path('system/health/', HealthCheckView.as_view(), name='health_check'),
    path('analytics/dashboard/', AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
    path('analytics/reports/export/', AnalyticsReportExportView.as_view(), name='analytics_reports_export'),
    
    path('', include(router.urls)),
]
