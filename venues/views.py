from rest_framework import viewsets, permissions, serializers
from .models import Venue, VenueImage, VenueCategory
from .serializers import (
    VenueSerializer, VenueListSerializer, VenueDetailSerializer,
    VenueImageSerializer, VenueCategorySerializer
)


class VenueCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for venue categories.
    Read access is public; write actions are restricted to admins.
    """
    queryset = VenueCategory.objects.all().order_by('name')
    serializer_class = VenueCategorySerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

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

class VenueImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling venue gallery images.
    """
    queryset = VenueImage.objects.all()
    serializer_class = VenueImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


