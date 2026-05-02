from django.contrib import admin
from .models import College, Department, SystemNotification, NotificationReadState

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'is_active', 'created_at')
    search_fields = ('name', 'abbreviation')
    list_filter = ('is_active',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'college', 'is_active', 'created_at')
    search_fields = ('name', 'slug')
    list_filter = ('college', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'target_all_users', 'is_active', 'expires_at', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('notification_type', 'target_all_users', 'is_active')
    filter_horizontal = ('target_roles', 'target_users')


@admin.register(NotificationReadState)
class NotificationReadStateAdmin(admin.ModelAdmin):
    list_display = ('notification', 'user', 'read_at')
    search_fields = ('notification__title', 'user__name', 'user__email')
    list_filter = ('read_at',)
