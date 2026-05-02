from django.db.models import Q
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer, BookingListSerializer, BookingDetailSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows venue bookings to be viewed or edited.
    """
    queryset = Booking.objects.filter(is_active=True).select_related('requester', 'club', 'venue', 'venue__category')
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self): # type: ignore
        if self.action == 'list':
            return BookingListSerializer
        if self.action == 'retrieve':
            return BookingDetailSerializer
        return BookingSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Ensure user has at least one role
        if not hasattr(user, 'roles') or not user.roles.exists():
            return queryset.none()

        role_slugs = set(user.roles.values_list('slug', flat=True))
        
        # Students should only see their own requests or their club's requests
        if 'general-student' in role_slugs:
            queryset = queryset.filter(requester=user)
        elif 'club-president' in role_slugs:
            queryset = queryset.filter(Q(requester=user) | Q(club__president=user))
             
        # Common filters
        status_param = self.request.query_params.get('status')
        venue = self.request.query_params.get('venue')
        club = self.request.query_params.get('club')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if status_param:
            queryset = queryset.filter(status=status_param)
        if venue:
            queryset = queryset.filter(venue_id=venue)
        if club:
            queryset = queryset.filter(club_id=club)
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
            
        return queryset

    def perform_create(self, serializer):
        # Automatically set requester to the logged-in user
        serializer.save(requester=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """
        Action for admins to approve a booking request.
        """
        booking = self.get_object()
        if booking.status != 'pending':
            return Response({'error': 'Booking is not in pending state'}, status=status.HTTP_400_BAD_REQUEST)
            
        booking.status = 'approved'
        booking.save()
        
        # Logic to create an event from the booking could be added here
        
        return Response({'status': 'approved'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def cancel(self, request, pk=None):
        """
        Action for admins to cancel a booking request.
        """
        booking = self.get_object()
        booking.status = 'cancelled'
        booking.save()
        return Response({'status': 'cancelled'}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Check venue availability",
        description="Check for available hourly time slots for a specific venue within a date range.",
        parameters=[
            OpenApiParameter("venue_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True, description="UUID of the venue", examples=[OpenApiExample("Example Venue", value="0fbf3330-4bcf-4317-be64-807d1ee261ca")]),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True, description="Start date (YYYY-MM-DD or ISO)", examples=[OpenApiExample("Example Start", value="2026-04-28")]),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True, description="End date (YYYY-MM-DD or ISO)", examples=[OpenApiExample("Example End", value="2026-04-30")]),
            OpenApiParameter("exclude_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="ID of a booking to exclude from conflict check (useful when editing)"),
        ],
        responses={200: OpenApiTypes.ANY}
    )
    @action(detail=False, methods=['get'])
    def availability(self, request):
        """
        Check for available time slots for a venue within a date range.
        Supports both snake_case and camelCase query parameters.
        """
        # Support both naming conventions
        venue_id = request.query_params.get('venue_id') or request.query_params.get('venueId')
        start_date = request.query_params.get('start_date') or request.query_params.get('startDate')
        end_date = request.query_params.get('end_date') or request.query_params.get('endDate')
        exclude_id = request.query_params.get('exclude_id') or request.query_params.get('excludeId')
        
        # Clean inputs and handle ISO timestamps (take only YYYY-MM-DD)
        venue_id = venue_id.strip() if venue_id else None
        start_date = start_date.strip().split('T')[0] if start_date else None
        end_date = end_date.strip().split('T')[0] if end_date else None
        
        if not all([venue_id, start_date, end_date]):
            return Response({
                'error': 'venue_id, start_date, and end_date are required',
                'received': {
                    'venue_id': venue_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'exclude_id': exclude_id,
                    'available_params': list(request.query_params.keys())
                }
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Overlapping check: (b.start_date <= end_date) AND (b.end_date >= start_date)
        # We consider both approved and pending bookings as "conflicts" to prevent double-booking attempts
        conflicting_bookings = Booking.objects.filter(
            venue_id=venue_id,
            status__in=['approved', 'pending'],
            start_date__lte=end_date,
            end_date__gte=start_date,
            is_active=True
        )
        
        if exclude_id:
            conflicting_bookings = conflicting_bookings.exclude(id=exclude_id)
        
        occupied_slots = set()
        for b in conflicting_bookings:
            slots = b.selected_slots if isinstance(b.selected_slots, list) else []
            for slot in slots:
                occupied_slots.add(slot)
                
        all_slots = [
            "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", 
            "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"
        ]
        
        availability_data = [
            {'label': slot, 'available': slot not in occupied_slots}
            for slot in all_slots
        ]
        
        return Response(availability_data)
