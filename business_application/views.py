from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate
)
from .forms import (
    BusinessApplicationForm, TechnicalServiceForm, ServiceDependencyForm, EventSourceForm, EventForm,
    MaintenanceForm, ChangeTypeForm, ChangeForm, IncidentForm, PagerDutyTemplateForm, TechnicalServicePagerDutyForm
)
from .tables import (
    BusinessApplicationTable, TechnicalServiceTable, ServiceDependencyTable,
    UpstreamDependencyTable, DownstreamDependencyTable, DownstreamBusinessApplicationTable,
    EventSourceTable, EventTable, MaintenanceTable, ChangeTypeTable, ChangeTable, IncidentTable,
    PagerDutyTemplateTable
)
from .filtersets import (
    BusinessApplicationFilter, TechnicalServiceFilter, ServiceDependencyFilter, EventSourceFilter, EventFilter,
    MaintenanceFilter, ChangeTypeFilter, ChangeFilter, IncidentFilter, PagerDutyTemplateFilter
)
from django.http import JsonResponse
from dcim.models import Device
from virtualization.models import VirtualMachine, Cluster

# BusinessApplication Views
class BusinessApplicationListView(generic.ObjectListView):
    queryset = BusinessApplication.objects.all()
    table = BusinessApplicationTable
    filterset = BusinessApplicationFilter

class BusinessApplicationChangeLogView(generic.ObjectChangeLogView):
    queryset = BusinessApplication.objects.all()

class BusinessApplicationDetailView(generic.ObjectView):
    queryset = BusinessApplication.objects.all()
    template_name = 'business_application/businessapplication/businessapplication.html'

class BusinessApplicationCreateView(generic.ObjectEditView):
    queryset = BusinessApplication.objects.all()
    form = BusinessApplicationForm

class BusinessApplicationEditView(generic.ObjectEditView):
    queryset = BusinessApplication.objects.all()
    form = BusinessApplicationForm

class BusinessApplicationDeleteView(generic.ObjectDeleteView):
    queryset = BusinessApplication.objects.all()

# TechnicalService Views
class TechnicalServiceListView(generic.ObjectListView):
    queryset = TechnicalService.objects.all()
    table = TechnicalServiceTable
    filterset = TechnicalServiceFilter

class TechnicalServiceChangeLogView(generic.ObjectChangeLogView):
    queryset = TechnicalService.objects.all()

@register_model_view(TechnicalService, name='operations', path='operations')
class TechnicalServiceOperationsView(generic.ObjectView):
    queryset = TechnicalService.objects.all()
    template_name = 'business_application/technicalservice/operations.html'

    tab = ViewTab(
        label='Operations',
        badge=lambda obj: obj.devices.count() + obj.vms.count() + obj.clusters.count(),
        permission='business_application.view_technicalservice',
        weight=100
    )

    def get(self, request, pk):
        obj = self.get_object(pk=pk)
        return render(
            request,
            self.template_name,
            context={
                'object': obj,
                'tab': self.tab,
            }
        )

@register_model_view(TechnicalService, name='dependencies', path='dependencies')
class TechnicalServiceDependenciesView(generic.ObjectView):
    queryset = TechnicalService.objects.all()
    template_name = 'business_application/technicalservice/dependencies.html'

    tab = ViewTab(
        label='Dependencies',
        badge=lambda obj: obj.get_upstream_dependencies().count() + obj.get_downstream_dependencies().count(),
        permission='business_application.view_technicalservice',
        weight=200
    )

    def get(self, request, pk):
        obj = self.get_object(pk=pk)

        # Get upstream and downstream dependencies
        upstream_deps = obj.get_upstream_dependencies()
        downstream_deps = obj.get_downstream_dependencies()
        downstream_apps = obj.get_downstream_business_applications()

        # Create table instances
        upstream_dependencies_table = UpstreamDependencyTable(upstream_deps)
        downstream_dependencies_table = DownstreamDependencyTable(downstream_deps)
        downstream_business_applications_table = DownstreamBusinessApplicationTable(downstream_apps)

        return render(
            request,
            self.template_name,
            context={
                'object': obj,
                'tab': self.tab,
                'upstream_dependencies_table': upstream_dependencies_table,
                'downstream_dependencies_table': downstream_dependencies_table,
                'downstream_business_applications_table': downstream_business_applications_table,
            }
        )

@register_model_view(TechnicalService, name='pagerduty', path='pagerduty')
class TechnicalServicePagerDutyView(generic.ObjectView):
    queryset = TechnicalService.objects.all()
    template_name = 'business_application/technicalservice/pagerduty.html'

    tab = ViewTab(
        label='PagerDuty',
        permission='business_application.view_technicalservice',
        weight=300
    )

    def get(self, request, pk):
        obj = self.get_object(pk=pk)
        return render(
            request,
            self.template_name,
            context={
                'object': obj,
                'tab': self.tab,
            }
        )

class TechnicalServicePagerDutyEditView(generic.ObjectEditView):
    queryset = TechnicalService.objects.all()
    form = TechnicalServicePagerDutyForm
    template_name = 'generic/object_edit.html'

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        return obj

class TechnicalServiceDetailView(generic.ObjectView):
    queryset = TechnicalService.objects.all()
    template_name = 'business_application/technicalservice.html'

class TechnicalServiceCreateView(generic.ObjectEditView):
    queryset = TechnicalService.objects.all()
    form = TechnicalServiceForm

class TechnicalServiceEditView(generic.ObjectEditView):
    queryset = TechnicalService.objects.all()
    form = TechnicalServiceForm

class TechnicalServiceDeleteView(generic.ObjectDeleteView):
    queryset = TechnicalService.objects.all()

# EventSource Views
class EventSourceListView(generic.ObjectListView):
    queryset = EventSource.objects.all()
    table = EventSourceTable
    filterset = EventSourceFilter

class EventSourceChangeLogView(generic.ObjectChangeLogView):
    queryset = EventSource.objects.all()

class EventSourceDetailView(generic.ObjectView):
    queryset = EventSource.objects.all()
    template_name = 'business_application/eventsource.html'

class EventSourceCreateView(generic.ObjectEditView):
    queryset = EventSource.objects.all()
    form = EventSourceForm

class EventSourceEditView(generic.ObjectEditView):
    queryset = EventSource.objects.all()
    form = EventSourceForm

class EventSourceDeleteView(generic.ObjectDeleteView):
    queryset = EventSource.objects.all()

# Event Views
class EventListView(generic.ObjectListView):
    queryset = Event.objects.all()
    table = EventTable
    filterset = EventFilter

class EventChangeLogView(generic.ObjectChangeLogView):
    queryset = Event.objects.all()

class EventDetailView(generic.ObjectView):
    queryset = Event.objects.all()
    template_name = 'business_application/event.html'

class EventCreateView(generic.ObjectEditView):
    queryset = Event.objects.all()
    form = EventForm

class EventEditView(generic.ObjectEditView):
    queryset = Event.objects.all()
    form = EventForm

class EventDeleteView(generic.ObjectDeleteView):
    queryset = Event.objects.all()

# Maintenance Views
class MaintenanceListView(generic.ObjectListView):
    queryset = Maintenance.objects.all()
    table = MaintenanceTable
    filterset = MaintenanceFilter

class MaintenanceChangeLogView(generic.ObjectChangeLogView):
    queryset = Maintenance.objects.all()

class MaintenanceDetailView(generic.ObjectView):
    queryset = Maintenance.objects.all()
    template_name = 'business_application/maintenance.html'

class MaintenanceCreateView(generic.ObjectEditView):
    queryset = Maintenance.objects.all()
    form = MaintenanceForm

class MaintenanceEditView(generic.ObjectEditView):
    queryset = Maintenance.objects.all()
    form = MaintenanceForm

class MaintenanceDeleteView(generic.ObjectDeleteView):
    queryset = Maintenance.objects.all()

# ChangeType Views
class ChangeTypeListView(generic.ObjectListView):
    queryset = ChangeType.objects.all()
    table = ChangeTypeTable
    filterset = ChangeTypeFilter

class ChangeTypeChangeLogView(generic.ObjectChangeLogView):
    queryset = ChangeType.objects.all()

class ChangeTypeDetailView(generic.ObjectView):
    queryset = ChangeType.objects.all()
    template_name = 'business_application/changetype.html'

class ChangeTypeCreateView(generic.ObjectEditView):
    queryset = ChangeType.objects.all()
    form = ChangeTypeForm

class ChangeTypeEditView(generic.ObjectEditView):
    queryset = ChangeType.objects.all()
    form = ChangeTypeForm

class ChangeTypeDeleteView(generic.ObjectDeleteView):
    queryset = ChangeType.objects.all()

# Change Views
class ChangeListView(generic.ObjectListView):
    queryset = Change.objects.all()
    table = ChangeTable
    filterset = ChangeFilter

class ChangeChangeLogView(generic.ObjectChangeLogView):
    queryset = Change.objects.all()

class ChangeDetailView(generic.ObjectView):
    queryset = Change.objects.all()
    template_name = 'business_application/change.html'

class ChangeCreateView(generic.ObjectEditView):
    queryset = Change.objects.all()
    form = ChangeForm

class ChangeEditView(generic.ObjectEditView):
    queryset = Change.objects.all()
    form = ChangeForm

class ChangeDeleteView(generic.ObjectDeleteView):
    queryset = Change.objects.all()

# Incident Views
class IncidentListView(generic.ObjectListView):
    queryset = Incident.objects.all()
    table = IncidentTable
    filterset = IncidentFilter

class IncidentChangeLogView(generic.ObjectChangeLogView):
    queryset = Incident.objects.all()

class IncidentDetailView(generic.ObjectView):
    queryset = Incident.objects.all()
    template_name = 'business_application/incident/incident.html'

class IncidentCreateView(generic.ObjectEditView):
    queryset = Incident.objects.all()
    form = IncidentForm

class IncidentEditView(generic.ObjectEditView):
    queryset = Incident.objects.all()
    form = IncidentForm

class IncidentDeleteView(generic.ObjectDeleteView):
    queryset = Incident.objects.all()

@register_model_view(Incident, name='timeline', path='timeline')
class IncidentTimelineView(generic.ObjectView):
    queryset = Incident.objects.all()
    template_name = 'business_application/incident/timeline.html'

    tab = ViewTab(
        label='Timeline',
        badge=lambda obj: obj.events.count(),
        permission='business_application.view_incident',
        weight=100
    )

    def get(self, request, pk):
        obj = self.get_object(pk=pk)

        # Get all events related to this incident
        events = obj.events.all().order_by('created_at')

        # Create timeline entries for events and their state changes
        timeline_entries = []

        # Add incident creation as first timeline entry
        timeline_entries.append({
            'timestamp': obj.created_at,
            'type': 'incident_created',
            'title': 'Incident Created',
            'description': f'Incident "{obj.title}" was created',
            'severity': obj.severity,
            'status': obj.status,
            'object': obj,
            'icon': 'mdi-alert-circle'
        })

        # Add events to timeline
        for event in events:
            timeline_entries.append({
                'timestamp': event.created_at,
                'type': 'event_added',
                'title': 'Event Added to Incident',
                'description': event.message,
                'severity': event.criticallity,
                'status': event.status,
                'object': event,
                'icon': 'mdi-plus-circle',
                'event_source': event.event_source.name if event.event_source else 'Unknown'
            })

            # If event was updated after creation, add update entry
            if event.updated_at > event.created_at:
                timeline_entries.append({
                    'timestamp': event.updated_at,
                    'type': 'event_updated',
                    'title': 'Event Updated',
                    'description': f'Event status changed: {event.message}',
                    'severity': event.criticallity,
                    'status': event.status,
                    'object': event,
                    'icon': 'mdi-pencil-circle',
                    'event_source': event.event_source.name if event.event_source else 'Unknown'
                })

        # Add incident status changes if resolved
        if obj.resolved_at:
            timeline_entries.append({
                'timestamp': obj.resolved_at,
                'type': 'incident_resolved',
                'title': 'Incident Resolved',
                'description': f'Incident "{obj.title}" was resolved',
                'severity': obj.severity,
                'status': 'resolved',
                'object': obj,
                'icon': 'mdi-check-circle'
            })

        # Add affected services information
        affected_services = obj.affected_services.all()
        if affected_services:
            timeline_entries.append({
                'timestamp': obj.created_at,
                'type': 'services_affected',
                'title': 'Affected Services',
                'description': f'{affected_services.count()} service(s) affected by this incident',
                'severity': obj.severity,
                'status': obj.status,
                'object': obj,
                'icon': 'mdi-server-network',
                'services': list(affected_services)
            })

        # Add responders if any
        responders = obj.responders.all()
        if responders:
            timeline_entries.append({
                'timestamp': obj.created_at,
                'type': 'responders_assigned',
                'title': 'Responders Assigned',
                'description': f'{responders.count()} responder(s) assigned to this incident',
                'severity': obj.severity,
                'status': obj.status,
                'object': obj,
                'icon': 'mdi-account-multiple',
                'responders': list(responders)
            })

        # Sort timeline entries by timestamp
        timeline_entries.sort(key=lambda x: x['timestamp'])

        return render(
            request,
            self.template_name,
            context={
                'object': obj,
                'tab': self.tab,
                'timeline_entries': timeline_entries,
                'events': events,
            }
        )

@register_model_view(TechnicalService, name='incidents_events', path='incidents-events')
class TechnicalServiceIncidentsEventsView(generic.ObjectView):
    queryset = TechnicalService.objects.all()
    template_name = 'business_application/technicalservice/incidents_events.html'

    tab = ViewTab(
        label='Incidents & Events',
        badge=lambda obj: obj.incidents.count() + Event.objects.filter(
            content_type__model__in=['device', 'virtualmachine', 'cluster'],
            object_id__in=list(obj.devices.values_list('id', flat=True)) +
                          list(obj.vms.values_list('id', flat=True)) +
                          list(obj.clusters.values_list('id', flat=True))
        ).count(),
        permission='business_application.view_technicalservice',
        weight=400
    )

    def get(self, request, pk):
        from django.contrib.contenttypes.models import ContentType
        obj = self.get_object(pk=pk)

        # Get incidents affecting this service
        incidents = obj.incidents.all().order_by('-created_at')

        # Get all events related to this service's infrastructure
        events = []
        timeline_entries = []

        # Get content types
        device_ct = ContentType.objects.get_for_model(Device)
        vm_ct = ContentType.objects.get_for_model(VirtualMachine)
        cluster_ct = ContentType.objects.get_for_model(Cluster)
        service_ct = ContentType.objects.get_for_model(TechnicalService)

        # Collect events from devices
        device_ids = list(obj.devices.values_list('id', flat=True))
        if device_ids:
            device_events = Event.objects.filter(
                content_type=device_ct,
                object_id__in=device_ids
            ).order_by('-created_at')
            events.extend(device_events)

        # Collect events from VMs
        vm_ids = list(obj.vms.values_list('id', flat=True))
        if vm_ids:
            vm_events = Event.objects.filter(
                content_type=vm_ct,
                object_id__in=vm_ids
            ).order_by('-created_at')
            events.extend(vm_events)

        # Collect events from clusters
        cluster_ids = list(obj.clusters.values_list('id', flat=True))
        if cluster_ids:
            cluster_events = Event.objects.filter(
                content_type=cluster_ct,
                object_id__in=cluster_ids
            ).order_by('-created_at')
            events.extend(cluster_events)

        # Collect events directly related to this service
        service_events = Event.objects.filter(
            content_type=service_ct,
            object_id=obj.id
        ).order_by('-created_at')
        events.extend(service_events)

        # Create timeline entries for incidents
        for incident in incidents:
            timeline_entries.append({
                'timestamp': incident.created_at,
                'type': 'incident_created',
                'title': 'Incident Created',
                'description': incident.title,
                'severity': incident.severity,
                'status': incident.status,
                'object': incident,
                'icon': 'mdi-alert-multiple',
                'related_object': obj
            })

            if incident.resolved_at:
                timeline_entries.append({
                    'timestamp': incident.resolved_at,
                    'type': 'incident_resolved',
                    'title': 'Incident Resolved',
                    'description': f'Incident "{incident.title}" was resolved',
                    'severity': incident.severity,
                    'status': 'resolved',
                    'object': incident,
                    'icon': 'mdi-check-circle',
                    'related_object': obj
                })

        # Create timeline entries for events
        for event in events:
            # Determine the infrastructure component
            if event.content_type == device_ct:
                infra_type = 'Device'
                try:
                    infra_name = Device.objects.get(id=event.object_id).name
                except Device.DoesNotExist:
                    infra_name = f'Device ID {event.object_id}'
            elif event.content_type == vm_ct:
                infra_type = 'VM'
                try:
                    infra_name = VirtualMachine.objects.get(id=event.object_id).name
                except VirtualMachine.DoesNotExist:
                    infra_name = f'VM ID {event.object_id}'
            elif event.content_type == cluster_ct:
                infra_type = 'Cluster'
                try:
                    infra_name = Cluster.objects.get(id=event.object_id).name
                except Cluster.DoesNotExist:
                    infra_name = f'Cluster ID {event.object_id}'
            else:
                infra_type = 'Service'
                infra_name = obj.name

            timeline_entries.append({
                'timestamp': event.created_at,
                'type': 'event',
                'title': f'Event on {infra_type}',
                'description': f'{event.message} ({infra_name})',
                'severity': event.criticallity,
                'status': event.status,
                'object': event,
                'icon': 'mdi-alert-circle-outline',
                'event_source': event.event_source.name if event.event_source else 'Unknown',
                'infra_type': infra_type,
                'infra_name': infra_name
            })

        # Get upstream services and their health status
        upstream_deps = obj.get_upstream_dependencies()
        upstream_services_health = []

        for dep in upstream_deps:
            upstream_service = dep.upstream_service
            health_status = upstream_service.health_status

            upstream_services_health.append({
                'service': upstream_service,
                'dependency': dep,
                'health_status': health_status,
                'is_degraded': health_status in ['degraded', 'down', 'under_maintenance'],
                'incidents_count': upstream_service.incidents.filter(
                    status__in=['new', 'investigating', 'identified']
                ).count()
            })

        # Sort timeline entries by timestamp (newest first)
        timeline_entries.sort(key=lambda x: x['timestamp'], reverse=True)

        # Get statistics
        stats = {
            'total_incidents': incidents.count(),
            'active_incidents': incidents.filter(status__in=['new', 'investigating', 'identified']).count(),
            'total_events': len(events),
            'triggered_events': len([e for e in events if e.status == 'triggered']),
            'critical_events': len([e for e in events if e.criticallity == 'CRITICAL']),
            'upstream_degraded': len([s for s in upstream_services_health if s['is_degraded']]),
        }

        return render(
            request,
            self.template_name,
            context={
                'object': obj,
                'tab': self.tab,
                'timeline_entries': timeline_entries[:50],  # Limit to 50 most recent
                'incidents': incidents,
                'events': events[:20],  # Limit to 20 most recent events
                'upstream_services_health': upstream_services_health,
                'stats': stats,
            }
        )

@register_model_view(BusinessApplication, name='incidents_events', path='incidents-events')
class BusinessApplicationIncidentsEventsView(generic.ObjectView):
    queryset = BusinessApplication.objects.all()
    template_name = 'business_application/businessapplication/incidents_events.html'

    tab = ViewTab(
        label='Incidents & Events',
        badge=lambda obj: Incident.objects.filter(
            affected_services__business_apps=obj
        ).distinct().count() + Event.objects.filter(
            content_type__model__in=['device', 'virtualmachine'],
            object_id__in=list(obj.devices.values_list('id', flat=True)) +
                          list(obj.virtual_machines.values_list('id', flat=True))
        ).count(),
        permission='business_application.view_businessapplication',
        weight=400
    )

    def get(self, request, pk):
        from django.contrib.contenttypes.models import ContentType
        obj = self.get_object(pk=pk)

        # Get incidents affecting services related to this business application
        related_services = obj.technical_services.all()
        incidents = Incident.objects.filter(
            affected_services__in=related_services
        ).distinct().order_by('-created_at')

        # Get all events related to this business application's infrastructure
        events = []
        timeline_entries = []

        # Get content types
        device_ct = ContentType.objects.get_for_model(Device)
        vm_ct = ContentType.objects.get_for_model(VirtualMachine)

        # Collect events from devices
        device_ids = list(obj.devices.values_list('id', flat=True))
        if device_ids:
            device_events = Event.objects.filter(
                content_type=device_ct,
                object_id__in=device_ids
            ).order_by('-created_at')
            events.extend(device_events)

        # Collect events from VMs
        vm_ids = list(obj.virtual_machines.values_list('id', flat=True))
        if vm_ids:
            vm_events = Event.objects.filter(
                content_type=vm_ct,
                object_id__in=vm_ids
            ).order_by('-created_at')
            events.extend(vm_events)

        # Create timeline entries for incidents
        for incident in incidents:
            # Find which services are affected
            affected_services = incident.affected_services.filter(
                business_apps=obj
            )

            timeline_entries.append({
                'timestamp': incident.created_at,
                'type': 'incident_created',
                'title': 'Incident Affects Business Application',
                'description': incident.title,
                'severity': incident.severity,
                'status': incident.status,
                'object': incident,
                'icon': 'mdi-alert-multiple',
                'affected_services': list(affected_services)
            })

            if incident.resolved_at:
                timeline_entries.append({
                    'timestamp': incident.resolved_at,
                    'type': 'incident_resolved',
                    'title': 'Incident Resolved',
                    'description': f'Incident "{incident.title}" was resolved',
                    'severity': incident.severity,
                    'status': 'resolved',
                    'object': incident,
                    'icon': 'mdi-check-circle',
                    'affected_services': list(affected_services)
                })

        # Create timeline entries for events
        for event in events:
            # Determine the infrastructure component
            if event.content_type == device_ct:
                infra_type = 'Device'
                try:
                    infra_name = Device.objects.get(id=event.object_id).name
                except Device.DoesNotExist:
                    infra_name = f'Device ID {event.object_id}'
            elif event.content_type == vm_ct:
                infra_type = 'VM'
                try:
                    infra_name = VirtualMachine.objects.get(id=event.object_id).name
                except VirtualMachine.DoesNotExist:
                    infra_name = f'VM ID {event.object_id}'
            else:
                infra_type = 'Unknown'
                infra_name = f'Object ID {event.object_id}'

            timeline_entries.append({
                'timestamp': event.created_at,
                'type': 'event',
                'title': f'Event on {infra_type}',
                'description': f'{event.message} ({infra_name})',
                'severity': event.criticallity,
                'status': event.status,
                'object': event,
                'icon': 'mdi-alert-circle-outline',
                'event_source': event.event_source.name if event.event_source else 'Unknown',
                'infra_type': infra_type,
                'infra_name': infra_name
            })

        # Sort timeline entries by timestamp (newest first)
        timeline_entries.sort(key=lambda x: x['timestamp'], reverse=True)

        # Get service health summary
        service_health_summary = {}
        for service in related_services:
            health_status = service.health_status
            if health_status not in service_health_summary:
                service_health_summary[health_status] = 0
            service_health_summary[health_status] += 1

        # Get statistics
        stats = {
            'total_incidents': incidents.count(),
            'active_incidents': incidents.filter(status__in=['new', 'investigating', 'identified']).count(),
            'total_events': len(events),
            'triggered_events': len([e for e in events if e.status == 'triggered']),
            'critical_events': len([e for e in events if e.criticallity == 'CRITICAL']),
            'total_services': related_services.count(),
            'degraded_services': len([s for s in related_services if s.health_status in ['degraded', 'down', 'under_maintenance']]),
        }

        return render(
            request,
            self.template_name,
            context={
                'object': obj,
                'tab': self.tab,
                'timeline_entries': timeline_entries[:50],  # Limit to 50 most recent
                'incidents': incidents,
                'events': events[:20],  # Limit to 20 most recent events
                'related_services': related_services,
                'service_health_summary': service_health_summary,
                'stats': stats,
            }
        )

@register_model_view(Device, name='events', path='events')
class DeviceEventsView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = 'business_application/device/events.html'

    tab = ViewTab(
        label='Events',
        badge=lambda obj: Event.objects.filter(content_type__model='device', object_id=obj.pk).count(),
        permission='dcim.view_device',
        weight=500
    )

    def get(self, request, pk):
        from django.contrib.contenttypes.models import ContentType
        obj = self.get_object(pk=pk)

        # Get device content type
        device_ct = ContentType.objects.get_for_model(Device)

        # Get all events related to this device
        events = Event.objects.filter(
            content_type=device_ct,
            object_id=obj.pk
        ).order_by('-created_at')

        # Get related technical services for this device
        related_services = obj.technical_services.all()

        # Get incidents that affect services related to this device
        related_incidents = Incident.objects.filter(
            affected_services__in=related_services
        ).distinct()

        # Create event timeline entries
        timeline_entries = []

        # Add events to timeline
        for event in events:
            timeline_entries.append({
                'timestamp': event.created_at,
                'type': 'event',
                'title': 'Event Recorded',
                'description': event.message,
                'severity': event.criticallity,
                'status': event.status,
                'object': event,
                'icon': 'mdi-alert-circle-outline',
                'event_source': event.event_source.name if event.event_source else 'Unknown',
                'dedup_id': event.dedup_id
            })

            # If event was updated after creation, add update entry
            if event.updated_at > event.created_at:
                timeline_entries.append({
                    'timestamp': event.updated_at,
                    'type': 'event_updated',
                    'title': 'Event Updated',
                    'description': f'Event status changed: {event.message}',
                    'severity': event.criticallity,
                    'status': event.status,
                    'object': event,
                    'icon': 'mdi-pencil-circle-outline',
                    'event_source': event.event_source.name if event.event_source else 'Unknown',
                    'dedup_id': event.dedup_id
                })

        # Sort timeline entries by timestamp (newest first)
        timeline_entries.sort(key=lambda x: x['timestamp'], reverse=True)

        # Get event statistics
        event_stats = {
            'total': events.count(),
            'triggered': events.filter(status='triggered').count(),
            'ok': events.filter(status='ok').count(),
            'suppressed': events.filter(status='suppressed').count(),
            'critical': events.filter(criticallity='CRITICAL').count(),
            'warning': events.filter(criticallity='WARNING').count(),
            'info': events.filter(criticallity='INFO').count(),
        }

        return render(
            request,
            self.template_name,
            context={
                'object': obj,
                'tab': self.tab,
                'timeline_entries': timeline_entries,
                'events': events,
                'related_services': related_services,
                'related_incidents': related_incidents,
                'event_stats': event_stats,
            }
        )

# ServiceDependency Views
class ServiceDependencyListView(generic.ObjectListView):
    queryset = ServiceDependency.objects.all()
    table = ServiceDependencyTable
    filterset = ServiceDependencyFilter

class ServiceDependencyChangeLogView(generic.ObjectChangeLogView):
    queryset = ServiceDependency.objects.all()

class ServiceDependencyDetailView(generic.ObjectView):
    queryset = ServiceDependency.objects.all()
    template_name = 'business_application/servicedependency/servicedependency.html'

class ServiceDependencyCreateView(generic.ObjectEditView):
    queryset = ServiceDependency.objects.all()
    form = ServiceDependencyForm

class ServiceDependencyEditView(generic.ObjectEditView):
    queryset = ServiceDependency.objects.all()
    form = ServiceDependencyForm

class ServiceDependencyDeleteView(generic.ObjectDeleteView):
    queryset = ServiceDependency.objects.all()

# PagerDuty Template Views
class PagerDutyTemplateListView(generic.ObjectListView):
    queryset = PagerDutyTemplate.objects.all()
    table = PagerDutyTemplateTable
    filterset = PagerDutyTemplateFilter

class PagerDutyTemplateDetailView(generic.ObjectView):
    queryset = PagerDutyTemplate.objects.all()
    template_name = 'business_application/pagerdutytemplate/pagerdutytemplate.html'

class PagerDutyTemplateCreateView(generic.ObjectEditView):
    queryset = PagerDutyTemplate.objects.all()
    form = PagerDutyTemplateForm

class PagerDutyTemplateEditView(generic.ObjectEditView):
    queryset = PagerDutyTemplate.objects.all()
    form = PagerDutyTemplateForm

class PagerDutyTemplateDeleteView(generic.ObjectDeleteView):
    queryset = PagerDutyTemplate.objects.all()



# Calendar View
class CalendarView(TemplateView):
    template_name = 'business_application/calendar.html'

    def get_context_data(self, **kwargs):
        def format_event_title(obj):
            title = ''
            if isinstance(obj, Incident):
                title = obj.title
            elif isinstance(obj, Maintenance):
                title = obj.description
            elif isinstance(obj, Change):
                title = obj.description
            if len(title) > 50:
                return title[:50] + '...'
            return title

        context = super().get_context_data(**kwargs)

        # Get filter parameters from request
        selected_apps = self.request.GET.getlist('business_apps')
        selected_services = self.request.GET.getlist('services')
        include_dependents = self.request.GET.get('include_dependents', False)

        # Date range - default to current month
        now = timezone.now()
        start_date = datetime(now.year, now.month, 1)
        if now.month == 12:
            end_date = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)

        # Override with URL parameters if provided
        if self.request.GET.get('start_date'):
            start_date = datetime.strptime(self.request.GET.get('start_date'), '%Y-%m-%d')
        if self.request.GET.get('end_date'):
            end_date = datetime.strptime(self.request.GET.get('end_date'), '%Y-%m-%d')

        # Build filters for incidents based on affected services
        incidents_filter = Q()
        maintenance_filter = Q()
        changes_filter = Q()

        if selected_apps:
            # Filter incidents for services related to selected business apps
            app_services = TechnicalService.objects.filter(
                business_apps__id__in=selected_apps
            ).values_list('id', flat=True)
            incidents_filter |= Q(affected_services__id__in=app_services)

            # Extend selected services with app services
            selected_services = list(set(selected_services) | set(app_services))

            # Filter maintenance/changes for devices/VMs related to selected business apps
            app_devices = BusinessApplication.objects.filter(
                id__in=selected_apps
            ).values_list('devices', flat=True)
            app_vms = BusinessApplication.objects.filter(
                id__in=selected_apps
            ).values_list('virtual_machines', flat=True)
            maintenance_filter |= Q(content_type__model='businessapplication', object_id__in=selected_apps)
            changes_filter |= Q(content_type__model='businessapplication', object_id__in=selected_apps)
            maintenance_filter |= Q(content_type__model='device', object_id__in=app_devices)
            maintenance_filter |= Q(content_type__model='virtualmachine', object_id__in=app_vms)
            changes_filter |= Q(content_type__model='device', object_id__in=app_devices)
            changes_filter |= Q(content_type__model='virtualmachine', object_id__in=app_vms)

        if selected_services:
            if include_dependents:
                previous = []
                current = set(selected_services)

                while previous != current:
                    previous = current
                    # Get downstream services from ServiceDependency relationships
                    downstream_services = ServiceDependency.objects.filter(
                        upstream_service__id__in=current
                    ).values_list('downstream_service_id', flat=True)
                    current = previous | set(downstream_services)

                selected_services = list(current)

            # Filter incidents for selected technical services
            incidents_filter |= Q(affected_services__id__in=selected_services)

            # Filter maintenance/changes for technical services and their related objects
            service_devices = TechnicalService.objects.filter(
                id__in=selected_services
            ).values_list('devices', flat=True)
            service_vms = TechnicalService.objects.filter(
                id__in=selected_services
            ).values_list('vms', flat=True)
            maintenance_filter |= Q(content_type__model='device', object_id__in=service_devices)
            maintenance_filter |= Q(content_type__model='virtualmachine', object_id__in=service_vms)
            maintenance_filter |= Q(content_type__model='technicalservice', object_id__in=selected_services)
            changes_filter |= Q(content_type__model='device', object_id__in=service_devices)
            changes_filter |= Q(content_type__model='virtualmachine', object_id__in=service_vms)
            changes_filter |= Q(content_type__model='technicalservice', object_id__in=selected_services)


        incidents = Incident.objects.filter(incidents_filter).filter(
            created_at__date__range=(start_date.date(), end_date.date())
        ).order_by('created_at') if incidents_filter else Incident.objects.filter(
            created_at__date__range=(start_date.date(), end_date.date())
        ).order_by('created_at')

        maintenances = Maintenance.objects.filter(maintenance_filter).filter(
            Q(planned_start__date__lt=end_date.date(), planned_end__date__gte=start_date.date())
        ).order_by('planned_start') if maintenance_filter else Maintenance.objects.filter(
            Q(planned_start__date__lt=end_date.date(), planned_end__date__gte=start_date.date())
        ).order_by('planned_start')

        changes = Change.objects.filter(changes_filter).filter(
            created_at__date__range=(start_date.date(), end_date.date())
        ).order_by('created_at') if changes_filter else Change.objects.filter(
            created_at__date__range=(start_date.date(), end_date.date())
        ).order_by('created_at')

        # Prepare data for calendar rendering
        calendar_events = []

        # Add incidents to calendar
        for incident in incidents:
            calendar_events.append({
                'title': format_event_title(incident),
                'start_ts': int(incident.created_at.timestamp() * 1000),
                'end_ts': int(incident.resolved_at.timestamp() * 1000) if incident.resolved_at else int(incident.created_at.timestamp() * 1000),
                'date': incident.created_at.strftime('%Y-%m-%d'),
                'time': incident.created_at.strftime('%H:%M'),
                'end_date': incident.resolved_at.strftime('%Y-%m-%d') if incident.resolved_at else None,
                'end_time': incident.resolved_at.strftime('%H:%M') if incident.resolved_at else None,
                'type': 'incident',
                'severity': incident.severity,
                'status': incident.status,
                'url': incident.get_absolute_url(),
                'object': incident
            })

        # Add maintenances to calendar
        for maintenance in maintenances:
            calendar_events.append({
                'title': format_event_title(maintenance),
                'start_ts': int(maintenance.planned_start.timestamp() * 1000),
                'end_ts': int(maintenance.planned_end.timestamp() * 1000),
                'date': maintenance.planned_start.strftime('%Y-%m-%d'),
                'time': maintenance.planned_start.strftime('%H:%M'),
                'end_date': maintenance.planned_end.strftime('%Y-%m-%d'),
                'end_time': maintenance.planned_end.strftime('%H:%M'),
                'type': 'maintenance',
                'status': maintenance.status,
                'url': maintenance.get_absolute_url(),
                'object': maintenance
            })

        # Add changes to calendar
        for change in changes:
            calendar_events.append({
                'title': format_event_title(change),
                'start_ts': int(change.created_at.timestamp() * 1000),
                'end_ts': int(change.created_at.timestamp() * 1000),
                'date': change.created_at.strftime('%Y-%m-%d'),
                'time': change.created_at.strftime('%H:%M'),
                'type': 'change',
                'change_type': change.type.name,
                'url': change.get_absolute_url(),
                'object': change
            })

        # Sort events by date and time
        calendar_events.sort(key=lambda x: (x['date'], x['time']))

        context.update({
            'calendar_events': calendar_events,
            'start_date': start_date,
            'end_date': end_date,
            'business_applications': BusinessApplication.objects.all(),
            'technical_services': TechnicalService.objects.all(),
            'selected_apps': selected_apps,
            'selected_services': selected_services,
            'include_dependents': include_dependents,
        })

        return context

# New view for dependency graph visualization
def dependency_graph_api(request, pk):  # pylint: disable=unused-argument
    """API endpoint to return dependency graph data for a technical service"""
    service = get_object_or_404(TechnicalService, pk=pk)

    def collect_all_dependencies(service, visited=None, depth=0, max_depth=3):
        """Recursively collect all upstream and downstream dependencies"""
        if visited is None:
            visited = set()

        if service.id in visited or depth > max_depth:
            return set(), set()

        visited.add(service.id)
        nodes = {service}
        links = set()

        # Get upstream dependencies
        for dep in service.get_upstream_dependencies():
            upstream_service = dep.upstream_service
            nodes.add(upstream_service)

            # Always add direct links - frontend will handle redundancy grouping
            links.add((upstream_service.id, service.id, dep.dependency_type, dep.name or f"Dependency {dep.id}"))

            # Recursively get upstream dependencies
            if depth < max_depth:
                upstream_nodes, upstream_links = collect_all_dependencies(
                    upstream_service, visited.copy(), depth + 1, max_depth
                )
                nodes.update(upstream_nodes)
                links.update(upstream_links)

        # Get downstream dependencies
        for dep in service.get_downstream_dependencies():
            downstream_service = dep.downstream_service
            nodes.add(downstream_service)

            # Always add direct links - frontend will handle redundancy grouping
            links.add((service.id, downstream_service.id, dep.dependency_type, dep.name or f"Dependency {dep.id}"))

            # Recursively get downstream dependencies
            if depth < max_depth:
                downstream_nodes, downstream_links = collect_all_dependencies(
                    downstream_service, visited.copy(), depth + 1, max_depth
                )
                nodes.update(downstream_nodes)
                links.update(downstream_links)

        return nodes, links

    # Collect all nodes and links
    all_nodes, all_links = collect_all_dependencies(service)

    # Convert to JSON format
    nodes_data = []
    for node in all_nodes:
        nodes_data.append({
            'id': node.id,
            'name': node.name,
            'service_type': node.service_type,
            'health_status': node.health_status,
            'node_type': 'service',
            'upstream_count': node.get_upstream_dependencies().count(),
            'downstream_count': node.get_downstream_dependencies().count(),
            'url': node.get_absolute_url()
        })

    links_data = []
    for source_id, target_id, link_type, link_name in all_links:
        links_data.append({
            'source': source_id,
            'target': target_id,
            'type': link_type,
            'name': link_name
        })

    return JsonResponse({
        'nodes': nodes_data,
        'links': links_data,
        'center_node': service.id
    })
