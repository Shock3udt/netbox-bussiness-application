from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from django.shortcuts import render
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
