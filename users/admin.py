from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Role, PasswordResetOTP

class RoleAdminForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.order_by('name'),
        required=False,
        widget=FilteredSelectMultiple('Users', is_stacked=False)
    )

    class Meta:
        model = Role
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['users'].initial = self.instance.users.all()

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    form = RoleAdminForm
    list_display = ('name', 'slug', 'is_staff_role', 'group_count', 'user_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug', 'description')
    filter_horizontal = ('groups',)

    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description', 'is_staff_role', 'groups', 'users')}),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.users.set(form.cleaned_data.get('users', []))

    @admin.display(description='Permission groups')
    def group_count(self, obj):
        return obj.groups.count()

    @admin.display(description='Assigned users')
    def user_count(self, obj):
        return obj.users.count()

@admin.action(description='Mark selected users as active')
def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description='Mark selected users as inactive')
def make_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'name', 'student_id', 'roles_list', 'department', 'is_staff', 'is_active']
    list_display_links = ['username', 'name']
    list_filter = ['roles', 'department', 'is_staff', 'is_active']
    search_fields = ['username', 'name', 'student_id', 'email']
    ordering = ['-created_at']
    list_per_page = 25
    actions = [make_active, make_inactive]

    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    autocomplete_fields = ['roles', 'department']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('name', 'email', 'avatar', 'phone_number')}),
        (_('Student Info'), {'fields': ('student_id', 'department', 'roles', 'dorm_block', 'dorm_room')}),
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
        (_('Student Info'), {'fields': ('name', 'student_id', 'department', 'roles', 'email', 'phone_number')}),
    )

    @admin.display(description='Roles')
    def roles_list(self, obj):
        return ", ".join(obj.roles.values_list('name', flat=True)) or "No roles"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('roles', 'department')


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'is_used', 'expires_at', 'created_at', 'attempts')
    search_fields = ('user__email', 'user__username', 'otp')
    list_filter = ('is_used',)
    readonly_fields = ('created_at',)

