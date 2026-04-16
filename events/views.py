from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Event
from .serializers import EventSerializer

class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """
    queryset = Event.objects.filter(is_active=True).select_related('organizing_club', 'venue').prefetch_related('attendees')
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status')
        club = self.request.query_params.get('club')
        
        # Special filtering for frontend "Live Now" or "Upcoming" sections
        if status_param == 'live-now':
            queryset = queryset.filter(status='live-now')
        elif status_param == 'upcoming':
            queryset = queryset.filter(status='upcoming')
        
        if club:
            queryset = queryset.filter(organizing_club_id=club)
            
        return queryset.order_by('schedule_date')

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
                return Response({'error': 'Event is full'}, status=status.HTTP_400_BAD_MESSAGE)
                
            event.attendees.add(user)
            att['current'] = current + 1
            event.attendance = att
            event.save()
            return Response({'status': 'attended', 'current': att['current']}, status=status.HTTP_200_OK)

