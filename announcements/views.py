from rest_framework import viewsets, permissions, filters, serializers
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied
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

    @staticmethod
    def _as_bool(value: str | None) -> bool:
        if value is None:
            return False
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}

    def get_queryset(self):  # type: ignore[override]
        queryset = self.queryset

        has_announcements = self._as_bool(self.request.GET.get('has_announcements'))
        published_only = self._as_bool(self.request.GET.get('published_only'))

        if has_announcements:
            queryset = queryset.filter(announcements__is_active=True)
            if published_only:
                queryset = queryset.filter(announcements__is_published=True)
            queryset = queryset.distinct()

        return queryset

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows announcements to be viewed or edited.
    Includes searching by title/tags and categorization filters.
    """
    queryset = Announcement.objects.filter(is_active=True).select_related('author', 'category').order_by('-created_at')
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
        
        user = self.request.user
        if not (user.is_authenticated and (user.is_staff or user.is_superuser)):
            queryset = queryset.filter(is_published=True)
            
        tag = self.request.query_params.get('tag')
        if tag:
            # Simple JSON contains query for tags list
            queryset = queryset.filter(tags__contains=[tag])
        return queryset

    def perform_create(self, serializer):
        if serializer.validated_data.get('category') is None:
            raise serializers.ValidationError({
                'category': ['Category is required. Please select a category before publishing.']
            })

        user = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
        serializer.save(author=user)

    def perform_update(self, serializer):
        if not self.request.user.has_perm('announcements.change_announcement'):
            raise PermissionDenied('You do not have permission to edit announcements.')
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm('announcements.delete_announcement'):
            raise PermissionDenied('You do not have permission to delete announcements.')
        instance.delete()

