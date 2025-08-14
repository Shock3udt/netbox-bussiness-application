from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from django.shortcuts import render, redirect, get_object_or_404
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
from django.http import HttpResponse, JsonResponse

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
def dependency_graph_api(request, pk):
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
