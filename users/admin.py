from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Role, PasswordResetOTP

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_staff_role', 'group')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')

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
    autocomplete_fields = ['role', 'department']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('name', 'email', 'avatar', 'phone_number')}),
        (_('Student Info'), {'fields': ('student_id', 'department', 'role', 'dorm_block', 'dorm_room')}),
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
        (_('Student Info'), {'fields': ('name', 'student_id', 'department', 'role', 'email', 'phone_number')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('role', 'department')


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'is_used', 'expires_at', 'created_at', 'attempts')
    search_fields = ('user__email', 'user__username', 'otp')
    list_filter = ('is_used',)
    readonly_fields = ('created_at',)

