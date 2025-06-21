import django_tables2 as tables
from netbox.tables import NetBoxTable
from .models import (
    BusinessApplication, TechnicalService, EventSource, Event,
    Maintenance, ChangeType, Change
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
    business_apps_count = tables.Column(verbose_name="Business Apps", accessor="business_apps.count")
    vms_count = tables.Column(verbose_name="VMs", accessor="vms.count")
    devices_count = tables.Column(verbose_name="Devices", accessor="devices.count")
    clusters_count = tables.Column(verbose_name="Clusters", accessor="clusters.count")

    class Meta(NetBoxTable.Meta):
        model = TechnicalService
        fields = ['name', 'parent', 'business_apps_count', 'vms_count', 'devices_count', 'clusters_count']

class EventSourceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    description = tables.Column()
    events_count = tables.Column(verbose_name="Events", accessor="event_set.count")

    class Meta(NetBoxTable.Meta):
        model = EventSource
        fields = ['name', 'description', 'events_count']

class EventTable(NetBoxTable):
    message = tables.Column(linkify=True)
    status = tables.Column()
    criticallity = tables.Column(verbose_name="Criticality")
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
