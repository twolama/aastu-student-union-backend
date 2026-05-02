from rest_framework import viewsets, permissions, status, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Club, ClubCategory
from .serializers import (
    ClubSerializer,
    ClubListSerializer,
    ClubDetailSerializer,
    ClubCategorySerializer,
)


class ClubCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for club categories.
    Read access is public; write actions are restricted to admins.
    """
    queryset = ClubCategory.objects.filter(is_active=True).order_by('name')
    serializer_class = ClubCategorySerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class ClubViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows clubs to be viewed or edited.
    """
    queryset = Club.objects.filter(is_active=True).select_related('president', 'category')
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self): # type: ignore
        if self.action == 'list':
            return ClubListSerializer
        if self.action == 'retrieve':
            return ClubDetailSerializer
        return ClubSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status')
        category = self.request.query_params.get('category')
        if status_param:
            queryset = queryset.filter(status=status_param)
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset

    def perform_create(self, serializer):
        if not self.request.user.has_perm('clubs.add_club'):
            raise PermissionDenied('You do not have permission to create clubs.')
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm('clubs.change_club'):
            raise PermissionDenied('You do not have permission to edit clubs.')
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm('clubs.delete_club'):
            raise PermissionDenied('You do not have permission to delete clubs.')
        instance.delete()

    @action(detail=True, methods=['get'], url_path='upcoming-events')
    def upcoming_events(self, request, pk=None):
        """
        Custom action to fetch upcoming events for a specific club.
        """
        club = self.get_object()
        # Ensure 'Event' is imported when needed or globally.
        from events.models import Event
        from events.serializers import EventSerializer
        from django.utils import timezone
        
        events = Event.objects.filter(
            organizing_club=club, 
            start_date_time__gte=timezone.now(),
            is_active=True
        ).order_by('start_date_time')[:5]
        
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

