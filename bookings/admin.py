from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Booking

@admin.action(description='Approve selected bookings')
def approve_booking(modeladmin, request, queryset):
    queryset.update(status='approved')

@admin.action(description='Cancel selected bookings')
def cancel_booking(modeladmin, request, queryset):
    queryset.update(status='cancelled')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id_label', 'requester', 'club', 'venue', 'status', 'requested_date_iso', 'is_active']
    list_display_links = ['id_label']
    list_filter = ['status', 'requested_date_iso', 'is_active', 'venue', 'club']
    search_fields = ['id_label', 'requester__name', 'club__name', 'venue__name', 'purpose']
    ordering = ['-requested_date_iso', '-created_at']
    list_per_page = 25
    list_editable = ['status', 'is_active']
    actions = [approve_booking, cancel_booking]

    readonly_fields = ['id', 'id_label', 'created_at', 'updated_at', 'deleted_at']
    autocomplete_fields = ['requester', 'club', 'venue', 'event']

    fieldsets = [
        (_('Booking Request'), {
            'fields': ('id', 'id_label', 'status', 'purpose')
        }),
        (_('Requester Info'), {
            'fields': ('requester', 'club', 'venue')
        }),
        (_('Scheduling'), {
            'fields': ('requested_date_iso', 'time_range')
        }),
        (_('Automation & Linkage'), {
            'fields': ('event',)
        }),
        (_('Audit Info'), {
            'fields': ('is_active', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('requester', 'club', 'venue')

