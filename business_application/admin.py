from django.contrib import admin
from .models import (
    BusinessApplication, TechnicalService, EventSource, Event,
    Maintenance, ChangeType, Change
)

@admin.register(BusinessApplication)
class BusinessApplicationAdmin(admin.ModelAdmin):
    list_display = ('appcode', 'name', 'owner', 'delegate')
    search_fields = ('appcode', 'name', 'owner')

@admin.register(TechnicalService)
class TechnicalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)
    list_filter = ('parent',)
    filter_horizontal = ('business_apps', 'vms', 'devices', 'clusters')

@admin.register(EventSource)
class EventSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('message', 'status', 'criticallity', 'event_source', 'last_seen_at')
    search_fields = ('message', 'dedup_id')
    list_filter = ('status', 'criticallity', 'event_source', 'created_at', 'last_seen_at')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = ('description', 'status', 'planned_start', 'planned_end', 'contact')
    search_fields = ('description', 'contact')
    list_filter = ('status', 'planned_start', 'planned_end')
    date_hierarchy = 'planned_start'

@admin.register(ChangeType)
class ChangeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

@admin.register(Change)
class ChangeAdmin(admin.ModelAdmin):
    list_display = ('description', 'type', 'created_at')
    search_fields = ('description',)
    list_filter = ('type', 'created_at')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
