from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from users.views import UserViewSet, ForgotPasswordView, ResetPasswordView, CustomTokenObtainPairView
from announcements.views import AnnouncementViewSet
from core.views import SystemStatsView, HealthCheckView
from bookings.views import BookingViewSet
from clubs.views import ClubViewSet
from events.views import EventViewSet, EventVolunteerViewSet
from users.views import UserViewSet
from venues.views import VenueViewSet

router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'clubs', ClubViewSet)
router.register(r'events', EventViewSet)
router.register(r'volunteers', EventVolunteerViewSet, basename='volunteer')
router.register(r'users', UserViewSet)
router.register(r'venues', VenueViewSet)

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
    
    path('', include(router.urls)),
]
