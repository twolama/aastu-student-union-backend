from django.utils import timezone
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import Event, EventVolunteer
from .serializers import (
    EventSerializer, EventListSerializer, EventDetailSerializer, EventVolunteerSerializer
)
from clubs.permissions import can_manage_club, get_managed_clubs, has_club_management_scope

class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """
    queryset = Event.objects.filter(is_active=True).select_related(
        'organizing_club',
        'venue',
        'venue__category',
        'booking',
        'booking__venue',
        'booking__venue__category',
    ).prefetch_related('attendees', 'volunteers', 'venue__gallery', 'booking__venue__gallery')
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self): # type: ignore
        if self.action == 'list':
            return EventListSerializer
        if self.action == 'retrieve':
            return EventDetailSerializer
        return EventSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if has_club_management_scope(user):
            managed_clubs = get_managed_clubs(user)
            queryset = queryset.filter(organizing_club__in=managed_clubs)

        status_param = self.request.query_params.get('status')
        club = self.request.query_params.get('club')
        now = timezone.now()
        
        # Determine status dynamically for queries to ensure real-time accuracy
        if status_param == 'live-now':
            queryset = queryset.filter(
                start_date_time__lte=now,
                end_date_time__gte=now
            )
        elif status_param == 'upcoming':
            queryset = queryset.filter(start_date_time__gt=now)
        elif status_param == 'archived':
            queryset = queryset.filter(end_date_time__lt=now)
        elif status_param:
            queryset = queryset.filter(status=status_param)
        
        if club:
            queryset = queryset.filter(organizing_club_id=club)
            
        return queryset.order_by('start_date_time')

    def _assert_club_scope(self, club):
        if not has_club_management_scope(self.request.user):
            return

        if can_manage_club(self.request.user, club):
            return

        managed_clubs = get_managed_clubs(self.request.user)
        if club is not None:
            raise PermissionDenied('You do not have permission to manage events for this club.')

    def perform_create(self, serializer):
        if not self.request.user.has_perm('events.add_event'):
            raise PermissionDenied('You do not have permission to create events.')
        self._assert_club_scope(serializer.validated_data.get('organizing_club'))
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm('events.change_event'):
            raise PermissionDenied('You do not have permission to edit events.')
        club = serializer.validated_data.get('organizing_club', serializer.instance.organizing_club)
        self._assert_club_scope(club)
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm('events.delete_event'):
            raise PermissionDenied('You do not have permission to delete events.')
        self._assert_club_scope(instance.organizing_club)
        instance.delete()

    @extend_schema(request=None)
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def attend(self, request, pk=None):
        """
        Toggle attendance for the currently authenticated user.
        """
        event = self.get_object()
        user = request.user
        
        if event.attendees.filter(id=user.id).exists():
            event.attendees.remove(user)
            # Update 'current' attendance in JSON
            att = event.attendance or {}
            att['current'] = max(0, att.get('current', 1) - 1)
            event.attendance = att
            event.save()
            return Response({'status': 'unattended', 'current': att['current']}, status=status.HTTP_200_OK)
        else:
            # Check capacity if provided
            att = event.attendance or {}
            capacity = att.get('capacity', 0)
            current = att.get('current', 0)
            
            if capacity > 0 and current >= capacity:
                return Response({'error': 'Event is full'}, status=status.HTTP_400_BAD_REQUEST)
                
            event.attendees.add(user)
            att['current'] = current + 1
            event.attendance = att
            event.save()
            return Response({'status': 'attended', 'current': att['current']}, status=status.HTTP_200_OK)

    @extend_schema(request=EventVolunteerSerializer)
    @action(detail=True, methods=['post'])
    def volunteer(self, request, pk=None):
        """
        Register a volunteer for this event.
        Requires: full_name, student_id, phone, email, role.
        """
        event = self.get_object()
        serializer = EventVolunteerSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(event=event)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EventVolunteerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual volunteers (Edit/Delete).
    """
    queryset = EventVolunteer.objects.filter(is_active=True)
    serializer_class = EventVolunteerSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

