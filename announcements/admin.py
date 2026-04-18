from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Announcement

@admin.action(description='Mark selected announcements as active')
def set_active(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'author_name', 'is_active', 'created_at']
    list_display_links = ['title']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['title', 'summary', 'author_name', 'tags']
    ordering = ['-created_at']
    list_per_page = 25
    list_editable = ['is_active']
    actions = [set_active]

    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    autocomplete_fields = ['author']

    fieldsets = [
        (_('Header'), {
            'fields': ('id', 'title', 'summary', 'category')
        }),
        (_('Author & Tags'), {
            'fields': ('author', 'author_name', 'tags')
        }),
        (_('Announcement Content'), {
            'fields': ('image', 'content_paragraphs', 'procedure_steps')
        }),
        (_('Audit Info'), {
            'fields': ('is_active', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author')

