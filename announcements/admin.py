from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Announcement, AnnouncementCategory

@admin.register(AnnouncementCategory)
class AnnouncementCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.action(description='Mark selected announcements as active')
def set_active(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'is_pinned', 'author_name', 'is_active', 'created_at']
    list_display_links = ['title']
    list_filter = ['category', 'is_pinned', 'is_active', 'created_at']
    search_fields = ['title', 'summary', 'author_name', 'tags']
    ordering = ['-is_pinned', '-created_at']
    list_per_page = 25
    list_editable = ['is_active', 'is_pinned']
    actions = [set_active]

    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    autocomplete_fields = ['author', 'category']

    fieldsets = [
        (_('Header'), {
            'fields': ('id', 'title', 'summary', 'category', 'is_pinned')
        }),
        (_('Author & Tags'), {
            'fields': ('author', 'author_name', 'tags')
        }),
        (_('Announcement Content'), {
            'fields': ('image', 'body', 'procedure_steps')
        }),
        (_('Audit Info'), {
            'fields': ('is_active', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author')

