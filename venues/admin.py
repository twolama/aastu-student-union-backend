from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Venue, VenueCategory, VenueImage

class VenueImageInline(admin.TabularInline):
    model = VenueImage
    extra = 1

@admin.action(description=_('Set selected venues to active'))
def set_active(modeladmin, request, queryset):
    queryset.update(status='active', is_active=True)

@admin.action(description=_('Set selected venues to maintenance'))
def set_maintenance(modeladmin, request, queryset):
    queryset.update(status='maintenance')

@admin.register(VenueCategory)
class VenueCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'status', 'max_capacity', 'campus_block', 'is_active']
    list_display_links = ['name']
    list_filter = ['status', 'category', 'is_active']
    search_fields = ['name', 'location', 'campus_block', 'nearby_landmarks']
    ordering = ['name']
    list_per_page = 25
    list_editable = ['status', 'is_active']
    actions = [set_active, set_maintenance]
    inlines = [VenueImageInline]

    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']

    fieldsets = [
        (_('Basic Information'), {
            'fields': ('id', 'name', 'category', 'status', 'is_active')
        }),
        (_('Capacity & Location'), {
            'fields': ('max_capacity', 'capacity_label', 'campus_block', 'floor_level', 'location', 'nearby_landmarks')
        }),
        (_('Descriptions'), {
            'fields': ('short_description', 'full_description')
        }),
        (_('Media Assets'), {
            'fields': ('hero_image', 'thumbnail', 'image_url')
        }),
        (_('Management & Amenities'), {
            'fields': ('manager_name', 'manager_phone', 'manager_email', 'amenities', 'contact')
        }),
        (_('Audit Info'), {
            'fields': ('deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]


