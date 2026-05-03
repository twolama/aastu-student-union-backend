from rest_framework import viewsets, permissions, serializers
from rest_framework.exceptions import PermissionDenied
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
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        if not self.request.user.has_perm('venues.add_venuecategory'):
            raise PermissionDenied('You do not have permission to create venue categories.')
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm('venues.change_venuecategory'):
            raise PermissionDenied('You do not have permission to edit venue categories.')
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm('venues.delete_venuecategory'):
            raise PermissionDenied('You do not have permission to delete venue categories.')
        instance.delete()

class VenueViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows venues to be viewed or edited.
    """
    queryset = Venue.objects.filter(is_active=True)
    serializer_class = VenueSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self) -> type[serializers.BaseSerializer]:  # type: ignore[override]
        if self.action == 'list':
            return VenueListSerializer
        if self.action == 'retrieve':
            return VenueDetailSerializer
        return VenueSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category__slug')
        if category:
            queryset = queryset.filter(category__slug=category)

        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def perform_create(self, serializer):
        if not self.request.user.has_perm('venues.add_venue'):
            raise PermissionDenied('You do not have permission to create venues.')
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm('venues.change_venue'):
            raise PermissionDenied('You do not have permission to edit venues.')
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm('venues.delete_venue'):
            raise PermissionDenied('You do not have permission to delete venues.')
        instance.delete()

class VenueImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling venue gallery images.
    """
    queryset = VenueImage.objects.all()
    serializer_class = VenueImageSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        if not (self.request.user.has_perm('venues.add_venueimage') or self.request.user.has_perm('venues.manage_venue_gallery')):
            raise PermissionDenied('You do not have permission to upload venue images.')
        serializer.save()

    def perform_update(self, serializer):
        if not (self.request.user.has_perm('venues.change_venueimage') or self.request.user.has_perm('venues.manage_venue_gallery')):
            raise PermissionDenied('You do not have permission to edit venue images.')
        serializer.save()

    def perform_destroy(self, instance):
        if not (self.request.user.has_perm('venues.delete_venueimage') or self.request.user.has_perm('venues.manage_venue_gallery')):
            raise PermissionDenied('You do not have permission to delete venue images.')
        instance.delete()


