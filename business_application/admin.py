from django.contrib import admin
from .models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate
)

@admin.register(BusinessApplication)
class BusinessApplicationAdmin(admin.ModelAdmin):
    list_display = ('appcode', 'name', 'owner', 'delegate')
    search_fields = ('appcode', 'name', 'owner')

@admin.register(TechnicalService)
class TechnicalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_type', 'has_pagerduty_integration', 'pagerduty_template_name')
    search_fields = ('name',)
    list_filter = ('service_type', 'pagerduty_template')
    filter_horizontal = ('business_apps', 'vms', 'devices', 'clusters')
    fieldsets = (
        (None, {
            'fields': ('name', 'service_type')
        }),
        ('Relationships', {
            'fields': ('business_apps', 'vms', 'devices', 'clusters')
        }),
        ('PagerDuty Integration', {
            'fields': ('pagerduty_service_definition', 'pagerduty_router_rule'),
            'description': 'Select PagerDuty templates to configure integration for this technical service.'
        }),
    )

    def has_pagerduty_integration(self, obj):
        return obj.has_pagerduty_integration
    has_pagerduty_integration.boolean = True
    has_pagerduty_integration.short_description = 'PagerDuty Configured'

    def pagerduty_template_name(self, obj):
        return obj.pagerduty_template_name or '-'
    pagerduty_template_name.short_description = 'PagerDuty Template'

@admin.register(PagerDutyTemplate)
class PagerDutyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'services_using_template', 'created', 'last_updated')
    search_fields = ('name', 'description')
    list_filter = ('template_type', 'created', 'last_updated')
    readonly_fields = ('services_using_template',)
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'template_type')
        }),
        ('PagerDuty Configuration', {
            'fields': ('pagerduty_config',),
            'description': 'Configure the PagerDuty service settings. Service definitions require specific fields, router rules have flexible configuration.'
        }),
        ('Usage', {
            'fields': ('services_using_template',),
            'description': 'Information about services currently using this template.'
        }),
    )

    def services_using_template(self, obj):
        count = obj.services_using_template
        if count > 0:
            return f"{count} service{'s' if count != 1 else ''}"
        return "No services"
    services_using_template.short_description = 'Services Using Template'

@admin.register(ServiceDependency)
class ServiceDependencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'upstream_service', 'downstream_service', 'dependency_type')
    search_fields = ('name', 'description', 'upstream_service__name', 'downstream_service__name')
    list_filter = ('dependency_type',)
    autocomplete_fields = ('upstream_service', 'downstream_service')

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

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'severity', 'created_at', 'resolved_at', 'commander')
    search_fields = ('title', 'description', 'reporter', 'commander')
    list_filter = ('status', 'severity', 'created_at', 'resolved_at')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    filter_horizontal = ('responders', 'affected_services', 'events')
