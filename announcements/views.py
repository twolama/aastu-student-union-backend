from rest_framework import viewsets, permissions, filters, serializers
from django_filters.rest_framework import DjangoFilterBackend
from .models import Announcement, AnnouncementCategory
from .serializers import (
    AnnouncementSerializer, AnnouncementListSerializer, AnnouncementDetailSerializer,
    AnnouncementCategorySerializer
)


class AnnouncementCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for announcement categories.
    Read access is public; write actions are restricted to admins.
    """
    queryset = AnnouncementCategory.objects.filter(is_active=True).order_by('name')
    serializer_class = AnnouncementCategorySerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows announcements to be viewed or edited.
    Includes searching by title/tags and categorization filters.
    """
    queryset = Announcement.objects.filter(is_active=True).select_related('author').order_by('-created_at')
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self): # type: ignore
        if self.action == 'list':
            return AnnouncementListSerializer
        if self.action == 'retrieve':
            return AnnouncementDetailSerializer
        return AnnouncementSerializer

    # Enable filtering and searching
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'author__username']
    search_fields = ['title', 'summary']
    ordering_fields = ['created_at', 'title']

    def get_queryset(self):
        queryset = super().get_queryset()
        tag = self.request.query_params.get('tag')
        if tag:
            # Simple JSON contains query for tags list
            queryset = queryset.filter(tags__contains=[tag])
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

