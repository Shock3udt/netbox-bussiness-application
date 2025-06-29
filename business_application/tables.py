import django_tables2 as tables
from netbox.tables import NetBoxTable
from .models import (
    BusinessApplication, TechnicalService, EventSource, Event,
    Maintenance, ChangeType, Change, Incident
)

class BusinessApplicationTable(NetBoxTable):
    name = tables.Column(linkify=True)
    appcode = tables.Column()
    owner = tables.Column()
    delegate = tables.Column()
    servicenow = tables.URLColumn(verbose_name="ServiceNow")

    class Meta(NetBoxTable.Meta):
        model = BusinessApplication
        fields = ['name', 'appcode', 'owner', 'delegate', 'servicenow']

class TechnicalServiceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    parent = tables.Column(linkify=True)
    dependencies_count = tables.Column(verbose_name="Dependencies", accessor="depends_on.count")
    business_apps_count = tables.Column(verbose_name="Business Apps", accessor="business_apps.count")
    vms_count = tables.Column(verbose_name="VMs", accessor="vms.count")
    devices_count = tables.Column(verbose_name="Devices", accessor="devices.count")
    clusters_count = tables.Column(verbose_name="Clusters", accessor="clusters.count")

    class Meta(NetBoxTable.Meta):
        model = TechnicalService
        fields = ['name', 'parent', 'dependencies_count', 'business_apps_count', 'vms_count', 'devices_count', 'clusters_count']

class EventSourceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    description = tables.Column()
    events_count = tables.Column(verbose_name="Events", accessor="event_set.count")

    class Meta(NetBoxTable.Meta):
        model = EventSource
        fields = ['name', 'description', 'events_count']

class EventTable(NetBoxTable):
    message = tables.Column(linkify=True)
    status = tables.TemplateColumn(
        template_code="""
        {% load helpers %}
        {% if record.status == 'triggered' %}
            <span class="badge bg-danger text-light"><i class="mdi mdi-alert-circle"></i> {{ record.get_status_display }}</span>
        {% elif record.status == 'ok' %}
            <span class="badge bg-success text-light"><i class="mdi mdi-check-circle"></i> {{ record.get_status_display }}</span>
        {% elif record.status == 'suppressed' %}
            <span class="badge bg-secondary text-light"><i class="mdi mdi-volume-off"></i> {{ record.get_status_display }}</span>
        {% else %}
            <span class="badge bg-light text-dark">{{ record.get_status_display }}</span>
        {% endif %}
        """,
        verbose_name="Status"
    )
    criticallity = tables.TemplateColumn(
        template_code="""
        {% load helpers %}
        {% if record.criticallity == 'critical' %}
            <span class="badge bg-danger text-light"><i class="mdi mdi-alert"></i> {{ record.get_criticallity_display }}</span>
        {% elif record.criticallity == 'warning' %}
            <span class="badge bg-warning text-dark"><i class="mdi mdi-alert-outline"></i> {{ record.get_criticallity_display }}</span>
        {% elif record.criticallity == 'info' %}
            <span class="badge bg-info text-light"><i class="mdi mdi-information"></i> {{ record.get_criticallity_display }}</span>
        {% else %}
            <span class="badge bg-light text-dark">{{ record.get_criticallity_display }}</span>
        {% endif %}
        """,
        verbose_name="Criticality"
    )
    event_source = tables.Column(linkify=True)
    last_seen_at = tables.DateTimeColumn()
    obj = tables.Column(verbose_name="Related Object")

    class Meta(NetBoxTable.Meta):
        model = Event
        fields = ['message', 'status', 'criticallity', 'event_source', 'last_seen_at', 'obj']

class MaintenanceTable(NetBoxTable):
    description = tables.Column(linkify=True)
    status = tables.Column()
    planned_start = tables.DateTimeColumn()
    planned_end = tables.DateTimeColumn()
    contact = tables.Column()
    obj = tables.Column(verbose_name="Affected Object")

    class Meta(NetBoxTable.Meta):
        model = Maintenance
        fields = ['description', 'status', 'planned_start', 'planned_end', 'contact', 'obj']

class ChangeTypeTable(NetBoxTable):
    name = tables.Column(linkify=True)
    description = tables.Column()
    changes_count = tables.Column(verbose_name="Changes", accessor="change_set.count")

    class Meta(NetBoxTable.Meta):
        model = ChangeType
        fields = ['name', 'description', 'changes_count']

class ChangeTable(NetBoxTable):
    description = tables.Column(linkify=True)
    type = tables.Column(linkify=True)
    created_at = tables.DateTimeColumn()
    obj = tables.Column(verbose_name="Affected Object")

    class Meta(NetBoxTable.Meta):
        model = Change
        fields = ['description', 'type', 'created_at', 'obj']

class IncidentTable(NetBoxTable):
    title = tables.Column(linkify=True)
    status = tables.TemplateColumn(
        template_code="""
        {% load business_app_filters %}
        {{ record.status|incident_status_badge }}
        """,
        verbose_name="Status"
    )
    severity = tables.TemplateColumn(
        template_code="""
        {% load business_app_filters %}
        {{ record.severity|incident_severity_badge }}
        """,
        verbose_name="Severity"
    )
    created_at = tables.DateTimeColumn()
    resolved_at = tables.DateTimeColumn()
    responders_count = tables.Column(verbose_name="Responders", accessor="responders.count")
    affected_services_count = tables.Column(verbose_name="Affected Services", accessor="affected_services.count")
    events_count = tables.Column(verbose_name="Events", accessor="events.count")
    commander = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = Incident
        fields = ['title', 'status', 'severity', 'created_at', 'resolved_at', 'responders_count', 'affected_services_count', 'events_count', 'commander']
