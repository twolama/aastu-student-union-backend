from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User

@admin.action(description='Mark selected users as active')
def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description='Mark selected users as inactive')
def make_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'name', 'student_id', 'role', 'department', 'is_staff', 'is_active']
    list_display_links = ['username', 'name']
    list_filter = ['role', 'department', 'is_staff', 'is_active']
    search_fields = ['username', 'name', 'student_id', 'email']
    ordering = ['-created_at']
    list_per_page = 25
    actions = [make_active, make_inactive]

    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('name', 'email', 'avatar_url')}),
        (_('Student Info'), {'fields': ('student_id', 'department', 'role')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Audit Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (_('Student Info'), {'fields': ('name', 'student_id', 'department', 'role', 'email')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request)

