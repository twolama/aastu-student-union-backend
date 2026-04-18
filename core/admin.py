from django.contrib import admin
from .models import College, Department

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
