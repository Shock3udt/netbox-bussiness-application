from re import T
from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    BusinessApplication, TechnicalService, EventSource, Event,
    Maintenance, ChangeType, Change
)
from .forms import (
    BusinessApplicationForm, TechnicalServiceForm, EventSourceForm, EventForm,
    MaintenanceForm, ChangeTypeForm, ChangeForm
)
from .tables import (
    BusinessApplicationTable, TechnicalServiceTable, EventSourceTable, EventTable,
    MaintenanceTable, ChangeTypeTable, ChangeTable
)
from .filtersets import (
    BusinessApplicationFilter, TechnicalServiceFilter, EventSourceFilter, EventFilter,
    MaintenanceFilter, ChangeTypeFilter, ChangeFilter
)

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

# Calendar View
class CalendarView(TemplateView):
    template_name = 'business_application/calendar.html'

    def get_context_data(self, **kwargs):
        def format_event_title(obj):
            title = ''
            if isinstance(obj, Event):
                title = obj.message
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
        selected_devices = self.request.GET.getlist('devices')
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

        # Build filters for related objects
        events_filter = Q()
        maintenance_filter = Q()
        changes_filter = Q()

        if selected_apps:
            # Filter events for devices/VMs related to selected business apps
            app_devices = BusinessApplication.objects.filter(
                id__in=selected_apps
            ).values_list('devices', flat=True)
            app_vms = BusinessApplication.objects.filter(
                id__in=selected_apps
            ).values_list('virtual_machines', flat=True)
            events_filter |= Q(content_type__model='device', object_id__in=app_devices)
            events_filter |= Q(content_type__model='virtualmachine', object_id__in=app_vms)
            maintenance_filter |= Q(content_type__model='device', object_id__in=app_devices)
            maintenance_filter |= Q(content_type__model='virtualmachine', object_id__in=app_vms)
            changes_filter |= Q(content_type__model='device', object_id__in=app_devices)
            changes_filter |= Q(content_type__model='virtualmachine', object_id__in=app_vms)

        if selected_services:
            # Filter for technical services and their related objects
            service_devices = TechnicalService.objects.filter(
                id__in=selected_services
            ).values_list('devices', flat=True)
            service_vms = TechnicalService.objects.filter(
                id__in=selected_services
            ).values_list('vms', flat=True)
            events_filter |= Q(content_type__model='device', object_id__in=service_devices)
            events_filter |= Q(content_type__model='virtualmachine', object_id__in=service_vms)
            maintenance_filter |= Q(content_type__model='device', object_id__in=service_devices)
            maintenance_filter |= Q(content_type__model='virtualmachine', object_id__in=service_vms)
            changes_filter |= Q(content_type__model='device', object_id__in=service_devices)
            changes_filter |= Q(content_type__model='virtualmachine', object_id__in=service_vms)

            # Include dependent services if requested
            if include_dependents:
                dependent_services = TechnicalService.objects.filter(
                    depends_on__id__in=selected_services
                )
                for service in dependent_services:
                    dep_devices = service.devices.values_list('id', flat=True)
                    dep_vms = service.vms.values_list('id', flat=True)
                    events_filter |= Q(content_type__model='device', object_id__in=dep_devices)
                    events_filter |= Q(content_type__model='virtualmachine', object_id__in=dep_vms)
                    maintenance_filter |= Q(content_type__model='device', object_id__in=dep_devices)
                    maintenance_filter |= Q(content_type__model='virtualmachine', object_id__in=dep_vms)
                    changes_filter |= Q(content_type__model='device', object_id__in=dep_devices)
                    changes_filter |= Q(content_type__model='virtualmachine', object_id__in=dep_vms)

        if selected_devices:
            events_filter |= Q(content_type__model='device', object_id__in=selected_devices)
            maintenance_filter |= Q(content_type__model='device', object_id__in=selected_devices)
            changes_filter |= Q(content_type__model='device', object_id__in=selected_devices)

        # Get filtered data within date range
        events = Event.objects.filter(events_filter).filter(
            last_seen_at__date__range=(start_date.date(), end_date.date())
        ).order_by('last_seen_at') if events_filter else Event.objects.filter(
            last_seen_at__date__range=(start_date.date(), end_date.date())
        ).order_by('last_seen_at')

        maintenances = Maintenance.objects.filter(maintenance_filter).filter(
            Q(planned_start__date__lt=end_date.date()) |
            Q(planned_end__date__gte=start_date.date())
        ).order_by('planned_start') if maintenance_filter else Maintenance.objects.filter(
            Q(planned_start__date__lt=end_date.date()) |
            Q(planned_end__date__gte=start_date.date())
        ).order_by('planned_start')

        changes = Change.objects.filter(changes_filter).filter(
            created_at__date__range=(start_date.date(), end_date.date())
        ).order_by('created_at') if changes_filter else Change.objects.filter(
            created_at__date__range=(start_date.date(), end_date.date())
        ).order_by('created_at')

        # Prepare data for calendar rendering
        calendar_events = []

        # Add events to calendar
        for event in events:
            calendar_events.append({
                'title': format_event_title(event),
                'start_ts': int(event.last_seen_at.timestamp() * 1000),
                'end_ts': int(event.last_seen_at.timestamp() * 1000),
                'date': event.last_seen_at.strftime('%Y-%m-%d'),
                'time': event.last_seen_at.strftime('%H:%M'),
                'type': 'event',
                'criticality': event.criticallity,
                'status': event.status,
                'url': event.get_absolute_url(),
                'object': event
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
                'end_ts': change.created_at.timestamp(),
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
            'selected_devices': selected_devices,
            'include_dependents': include_dependents,
        })

        return context
