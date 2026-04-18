from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Event

@admin.action(description='Set selected events to live now')
def set_live(modeladmin, request, queryset):
    queryset.update(status='live-now')

@admin.action(description='Archive selected events')
def set_archived(modeladmin, request, queryset):
    queryset.update(status='archived')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'organizing_club', 'venue', 'status', 'schedule_date', 'is_mega_event', 'is_active']
    list_display_links = ['title']
    list_filter = ['status', 'is_mega_event', 'schedule_date', 'is_active', 'organizing_club']
    search_fields = ['title', 'summary', 'organizing_club__name', 'venue__name']
    ordering = ['-schedule_date', '-created_at']
    list_per_page = 25
    list_editable = ['status', 'is_active']
    actions = [set_live, set_archived]

    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    autocomplete_fields = ['organizing_club', 'venue', 'attendees']
    
    fieldsets = [
        (_('Event Header'), {
            'fields': ('id', 'title', 'summary', 'status', 'is_mega_event')
        }),
        (_('Organization & Venue'), {
            'fields': ('organizing_club', 'venue')
        }),
        (_('Scheduling'), {
            'fields': ('schedule_date', 'schedule_time_range')
        }),
        (_('Internal Assets'), {
            'fields': ('cover_image', 'description', 'attendance')
        }),
        (_('Attendees List'), {
            'fields': ('attendees',),
            'classes': ('collapse',)
        }),
        (_('Audit Info'), {
            'fields': ('is_active', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organizing_club', 'venue')

