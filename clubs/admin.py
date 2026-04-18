from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Club

@admin.action(description='Set selected clubs to active')
def set_active(modeladmin, request, queryset):
    queryset.update(status='active', is_active=True)

@admin.action(description='Set selected clubs to pending')
def set_pending(modeladmin, request, queryset):
    queryset.update(status='pending')

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'status', 'category_label', 'president', 'is_active', 'created_at']
    list_display_links = ['name']
    list_filter = ['status', 'category_label', 'is_active', 'created_at']
    search_fields = ['name', 'president__name', 'president__student_id', 'advisor_name']
    ordering = ['-created_at']
    list_per_page = 30
    list_editable = ['status', 'is_active']
    actions = [set_active, set_pending]

    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    autocomplete_fields = ['president']

    fieldsets = [
        (_('Basic Information'), {
            'fields': ('id', 'name', 'status', 'category_label', 'location_label')
        }),
        (_('Club Details'), {
            'fields': ('president', 'advisor_name', 'description', 'links')
        }),
        (_('Media Assets'), {
            'fields': ('logo', 'cover_image')
        }),
        (_('Audit Info'), {
            'fields': ('is_active', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

    def get_queryset(self, request):
        """Optimize queries to avoid N+1"""
        return super().get_queryset(request).select_related('president')

