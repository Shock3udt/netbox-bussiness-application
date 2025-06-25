from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet
from .models import (
    BusinessApplication, TechnicalService, EventSource, Event,
    Maintenance, ChangeType, Change, Incident
)

class BusinessApplicationFilter(NetBoxModelFilterSet):
    """
    Filters for the BusinessApplication model.
    """

    def search(self, queryset, name, value):
        if not value:
            return queryset
        qs_filter = (
            Q(name__icontains=value)
            | Q(appcode__icontains=value)
        )
        return queryset.filter(qs_filter)

    class Meta:
        model = BusinessApplication
        fields = ['appcode', 'name', 'owner', 'delegate']

class TechnicalServiceFilter(NetBoxModelFilterSet):
    """
    Filters for the TechnicalService model.
    """

    def search(self, queryset, name, value):
        if not value:
            return queryset
        qs_filter = Q(name__icontains=value)
        return queryset.filter(qs_filter)

    class Meta:
        model = TechnicalService
        fields = ['name', 'parent']

class EventSourceFilter(NetBoxModelFilterSet):
    """
    Filters for the EventSource model.
    """

    def search(self, queryset, name, value):
        if not value:
            return queryset
        qs_filter = (
            Q(name__icontains=value)
            | Q(description__icontains=value)
        )
        return queryset.filter(qs_filter)

    class Meta:
        model = EventSource
        fields = ['name']

class EventFilter(NetBoxModelFilterSet):
    """
    Filters for the Event model.
    """

    def search(self, queryset, name, value):
        if not value:
            return queryset
        qs_filter = (
            Q(message__icontains=value)
            | Q(dedup_id__icontains=value)
        )
        return queryset.filter(qs_filter)

    class Meta:
        model = Event
        fields = ['status', 'criticallity', 'event_source']

class MaintenanceFilter(NetBoxModelFilterSet):
    """
    Filters for the Maintenance model.
    """

    def search(self, queryset, name, value):
        if not value:
            return queryset
        qs_filter = (
            Q(description__icontains=value)
            | Q(contact__icontains=value)
        )
        return queryset.filter(qs_filter)

    class Meta:
        model = Maintenance
        fields = ['status', 'contact']

class ChangeTypeFilter(NetBoxModelFilterSet):
    """
    Filters for the ChangeType model.
    """

    def search(self, queryset, name, value):
        if not value:
            return queryset
        qs_filter = (
            Q(name__icontains=value)
            | Q(description__icontains=value)
        )
        return queryset.filter(qs_filter)

    class Meta:
        model = ChangeType
        fields = ['name']

class ChangeFilter(NetBoxModelFilterSet):
    """
    Filters for the Change model.
    """

    def search(self, queryset, name, value):
        if not value:
            return queryset
        qs_filter = Q(description__icontains=value)
        return queryset.filter(qs_filter)

    class Meta:
        model = Change
        fields = ['type']

class IncidentFilter(NetBoxModelFilterSet):
    """
    Filters for the Incident model.
    """

    def search(self, queryset, name, value):
        if not value:
            return queryset
        qs_filter = (
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(reporter__icontains=value)
            | Q(commander__icontains=value)
        )
        return queryset.filter(qs_filter)

    class Meta:
        model = Incident
        fields = ['status', 'severity', 'responders', 'affected_services', 'reporter', 'commander']
