import django_tables2 as tables
from netbox.tables import NetBoxTable
from .models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate
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
    service_type = tables.TemplateColumn(
        template_code="""
        {% load helpers %}
        {% if record.service_type == 'technical' %}
            <span class="badge bg-primary text-light"><i class="mdi mdi-cog"></i> Technical</span>
        {% elif record.service_type == 'logical' %}
            <span class="badge bg-secondary text-light"><i class="mdi mdi-sitemap"></i> Logical</span>
        {% else %}
            <span class="badge bg-light text-dark">{{ record.get_service_type_display }}</span>
        {% endif %}
        """,
        verbose_name="Type"
    )
    health_status = tables.TemplateColumn(
        template_code="""
        {% load helpers %}
        {% if record.health_status == 'down' %}
            <span class="badge bg-danger text-light"><i class="mdi mdi-alert-circle"></i> Down</span>
        {% elif record.health_status == 'degraded' %}
            <span class="badge bg-warning text-dark"><i class="mdi mdi-alert-outline"></i> Degraded</span>
        {% elif record.health_status == 'under_maintenance' %}
            <span class="badge bg-info text-light"><i class="mdi mdi-wrench"></i> Under Maintenance</span>
        {% elif record.health_status == 'healthy' %}
            <span class="badge bg-success text-light"><i class="mdi mdi-check-circle"></i> Healthy</span>
        {% else %}
            <span class="badge bg-light text-dark">{{ record.health_status|title }}</span>
        {% endif %}
        """,
        verbose_name="Health Status"
    )
    upstream_dependencies_count = tables.Column(verbose_name="Upstream", accessor="upstream_dependencies.count")
    downstream_dependencies_count = tables.Column(verbose_name="Downstream", accessor="downstream_dependencies.count")
    business_apps_count = tables.Column(verbose_name="Business Apps", accessor="business_apps.count")
    vms_count = tables.Column(verbose_name="VMs", accessor="vms.count")
    devices_count = tables.Column(verbose_name="Devices", accessor="devices.count")
    clusters_count = tables.Column(verbose_name="Clusters", accessor="clusters.count")
    pagerduty_integration = tables.TemplateColumn(
        template_code='''
        {% if record.has_pagerduty_integration %}
            <span class="badge bg-success"><i class="mdi mdi-check"></i> Complete</span>
        {% elif record.pagerduty_service_definition or record.pagerduty_router_rule %}
            <span class="badge bg-warning"><i class="mdi mdi-alert"></i> Partial</span>
        {% else %}
            <span class="badge bg-light text-dark"><i class="mdi mdi-minus"></i> None</span>
        {% endif %}
        ''',
        verbose_name="PagerDuty"
    )

    class Meta(NetBoxTable.Meta):
        model = TechnicalService
        fields = ['name', 'service_type', 'health_status', 'pagerduty_integration', 'upstream_dependencies_count', 'downstream_dependencies_count', 'business_apps_count', 'vms_count', 'devices_count', 'clusters_count']

class PagerDutyTemplateTable(NetBoxTable):
    name = tables.Column(linkify=True)
    template_type = tables.TemplateColumn(
        template_code='''
        {% if record.template_type == "service_definition" %}
            <span class="badge bg-primary">Service Definition</span>
        {% elif record.template_type == "router_rule" %}
            <span class="badge bg-info">Router Rule</span>
        {% else %}
            {{ record.get_template_type_display }}
        {% endif %}
        ''',
        verbose_name="Type"
    )
    services_count = tables.Column(verbose_name="Services Using", accessor="services_using_template")

    class Meta(NetBoxTable.Meta):
        model = PagerDutyTemplate
        fields = ['name', 'template_type', 'description', 'services_count', 'created', 'last_updated']

class ServiceDependencyTable(NetBoxTable):
    name = tables.Column(linkify=True)
    upstream_service = tables.Column(linkify=True)
    downstream_service = tables.Column(linkify=True)
    dependency_type = tables.TemplateColumn(
        template_code="""
        {% load helpers %}
        {% if record.dependency_type == 'normal' %}
            <span class="badge bg-warning text-dark"><i class="mdi mdi-link"></i> Normal</span>
        {% elif record.dependency_type == 'redundancy' %}
            <span class="badge bg-success text-light"><i class="mdi mdi-backup-restore"></i> Redundancy</span>
        {% else %}
            <span class="badge bg-light text-dark">{{ record.get_dependency_type_display }}</span>
        {% endif %}
        """,
        verbose_name="Type"
    )
    description = tables.Column(verbose_name="Description")

    class Meta(NetBoxTable.Meta):
        model = ServiceDependency
        fields = ['name', 'upstream_service', 'downstream_service', 'dependency_type', 'description']

class UpstreamDependencyTable(NetBoxTable):
    """Table for showing upstream dependencies of a service"""
    name = tables.Column(linkify=True, verbose_name="Dependency Name")
    upstream_service = tables.Column(linkify=True, verbose_name="Upstream Service")
    dependency_type = tables.TemplateColumn(
        template_code="""
        {% load helpers %}
        {% if record.dependency_type == 'normal' %}
            <span class="badge bg-warning text-dark"><i class="mdi mdi-link"></i> Normal</span>
        {% elif record.dependency_type == 'redundancy' %}
            <span class="badge bg-success text-light"><i class="mdi mdi-backup-restore"></i> Redundancy</span>
        {% else %}
            <span class="badge bg-light text-dark">{{ record.get_dependency_type_display }}</span>
        {% endif %}
        """,
        verbose_name="Type"
    )
    description = tables.Column(verbose_name="Description")

    class Meta(NetBoxTable.Meta):
        model = ServiceDependency
        fields = ['name', 'upstream_service', 'dependency_type', 'description']

class DownstreamDependencyTable(NetBoxTable):
    """Table for showing downstream dependencies of a service"""
    name = tables.Column(linkify=True, verbose_name="Dependency Name")
    downstream_service = tables.Column(linkify=True, verbose_name="Downstream Service")
    dependency_type = tables.TemplateColumn(
        template_code="""
        {% load helpers %}
        {% if record.dependency_type == 'normal' %}
            <span class="badge bg-warning text-dark"><i class="mdi mdi-link"></i> Normal</span>
        {% elif record.dependency_type == 'redundancy' %}
            <span class="badge bg-success text-light"><i class="mdi mdi-backup-restore"></i> Redundancy</span>
        {% else %}
            <span class="badge bg-light text-dark">{{ record.get_dependency_type_display }}</span>
        {% endif %}
        """,
        verbose_name="Type"
    )
    description = tables.Column(verbose_name="Description")

    class Meta(NetBoxTable.Meta):
        model = ServiceDependency
        fields = ['name', 'downstream_service', 'dependency_type', 'description']

class DownstreamBusinessApplicationTable(NetBoxTable):
    """Table for showing downstream business applications affected by a service"""
    name = tables.Column(linkify=True)
    appcode = tables.Column()
    owner = tables.Column()
    delegate = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = BusinessApplication
        fields = ['name', 'appcode', 'owner', 'delegate']

class EventSourceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    description = tables.Column()
    events_count = tables.Column(verbose_name="Events", accessor="event_set.count")

    class Meta(NetBoxTable.Meta):
        model = EventSource
        fields = ['name', 'description', 'events_count']

class EventTable(NetBoxTable):
    pk = tables.CheckBoxColumn()
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
    obj = tables.TemplateColumn(
        template_code="""
        {% load helpers %}
        {% if record.has_valid_target %}
            {{ record.obj }}
        {% else %}
            <span class="text-danger"><i class="mdi mdi-alert-circle-outline"></i> Invalid Target</span>
        {% endif %}
        """,
        verbose_name="Related Object"
    )
    is_valid = tables.TemplateColumn(
        template_code="""
        {% load helpers %}
        {% if record.is_valid %}
            <span class="badge bg-success text-light"><i class="mdi mdi-check-circle"></i> Valid</span>
        {% else %}
            <span class="badge bg-danger text-light"><i class="mdi mdi-alert-circle"></i> Invalid</span>
        {% endif %}
        """,
        verbose_name="Validity"
    )

    class Meta(NetBoxTable.Meta):
        model = Event
        fields = ['pk', 'message', 'status', 'criticallity', 'event_source', 'last_seen_at', 'obj', 'is_valid']

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
    pk = tables.CheckBoxColumn()
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
    affected_devices_count = tables.Column(verbose_name="Affected Devices", accessor="affected_devices.count")
    events_count = tables.Column(verbose_name="Events", accessor="events.count")
    commander = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = Incident
        fields = ['pk', 'title', 'status', 'severity', 'created_at', 'resolved_at', 'responders_count', 'affected_services_count', 'affected_devices_count', 'events_count', 'commander']
