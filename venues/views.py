from rest_framework import viewsets, permissions, serializers
from .models import Venue
from .serializers import (
    VenueSerializer, VenueListSerializer, VenueDetailSerializer
)

class VenueViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows venues to be viewed or edited.
    """
    queryset = Venue.objects.filter(is_active=True)
    serializer_class = VenueSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self) -> type[serializers.BaseSerializer]:
        if self.action == 'list':
            return VenueListSerializer
        if self.action == 'retrieve':
            return VenueDetailSerializer
        return VenueSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

