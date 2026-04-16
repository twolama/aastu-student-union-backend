from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Club
from .serializers import ClubSerializer

class ClubViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows clubs to be viewed or edited.
    """
    queryset = Club.objects.filter(is_active=True).select_related('president')
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status')
        category = self.request.query_params.get('category')
        if status_param:
            queryset = queryset.filter(status=status_param)
        if category:
            queryset = queryset.filter(category_label=category)
        return queryset

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
            organizer=club, 
            schedule_date__gte=timezone.now().date(),
            is_active=True
        ).order_by('schedule_date')[:5]
        
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

