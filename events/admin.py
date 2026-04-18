from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Event, EventVolunteer

class EventVolunteerInline(admin.TabularInline):
    model = EventVolunteer
    extra = 1

@admin.action(description='Set selected events to live now')
def set_live(modeladmin, request, queryset):
    queryset.update(status='live-now')

@admin.action(description='Archive selected events')
def set_archived(modeladmin, request, queryset):
    queryset.update(status='archived')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'organizing_club', 'venue', 'status', 'start_date_time', 'is_mega_event', 'is_archived', 'is_active']
    list_display_links = ['title']
    list_filter = ['status', 'is_mega_event', 'is_archived', 'start_date_time', 'is_active', 'organizing_club']
    search_fields = ['title', 'short_description', 'organizing_club__name', 'venue__name']
    ordering = ['-start_date_time', '-created_at']
    list_per_page = 25
    list_editable = ['status', 'is_active', 'is_archived']
    actions = [set_live, set_archived]

    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    autocomplete_fields = ['organizing_club', 'venue', 'attendees']
    inlines = [EventVolunteerInline]
    
    fieldsets = [
        (_('Event Header'), {
            'fields': ('id', 'title', 'short_description', 'status', 'is_mega_event', 'is_archived', 'registration_link')
        }),
        (_('Organization & Venue'), {
            'fields': ('organizing_club', 'venue', 'physical_location_details', 'max_capacity')
        }),
        (_('Scheduling'), {
            'fields': ('start_date_time', 'end_date_time')
        }),
        (_('Internal Assets'), {
            'fields': ('cover_image', 'description', 'attendance', 'logistics')
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

