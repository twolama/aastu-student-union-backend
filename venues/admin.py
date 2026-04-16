from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Venue

@admin.action(description='Set selected venues to active')
def set_active(modeladmin, request, queryset):
    queryset.update(status='active', is_active=True)

@admin.action(description='Set selected venues to maintenance')
def set_maintenance(modeladmin, request, queryset):
    queryset.update(status='maintenance')

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type_label', 'status', 'capacity_label', 'location', 'is_active']
    list_display_links = ['name']
    list_filter = ['status', 'type_label', 'is_active']
    search_fields = ['name', 'location', 'type_label']
    ordering = ['name']
    list_per_page = 25
    list_editable = ['status', 'is_active']
    actions = [set_active, set_maintenance]

    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']

    fieldsets = [
        (_('Basic Information'), {
            'fields': ('id', 'name', 'status', 'type_label', 'location')
        }),
        (_('Venue Details'), {
            'fields': ('capacity_label', 'amenities', 'contact', 'image_url')
        }),
        (_('Audit Info'), {
            'fields': ('is_active', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

