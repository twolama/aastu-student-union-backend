from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer

class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows venue bookings to be viewed or edited.
    """
    queryset = Booking.objects.filter(is_active=True).select_related('requester', 'club', 'venue')
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students should only see their own requests or their club's requests
        if user.role == 'general-student':
             queryset = queryset.filter(requester=user)
        elif user.role == 'club-president':
             queryset = queryset.filter(models.Q(requester=user) | models.Q(club__president=user))
             
        # Admin can filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
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
            return Response({'error': 'Booking is not in pending state'}, status=status.HTTP_400_BAD_MESSAGE)
            
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
